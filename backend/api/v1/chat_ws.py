"""WebSocket Duplex Streaming Route for Enterprise AI Digital Assistant with DB Persistence."""

import asyncio
from datetime import datetime
import json
import logging
import re
from typing import Dict, List, Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.errors import GraphInterrupt

from backend.core.exceptions import AuthenticationError
from backend.core.guardrails import StreamingSanitizer, sanitize_text, validate_input
from backend.core.metrics import record_ttft, set_active_ws_connections
from backend.core.rbac import UserPayload, resolve_user_from_token
from backend.core.task_manager import task_manager
from backend.db.session import SessionLocal
from backend.graph.state import AgentState
from backend.graph.workflow import graph
from backend.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["WebSocket Chat"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        set_active_ws_connections(len(self.active_connections))

    def disconnect(self, client_id: str, websocket: Optional[WebSocket] = None):
        if client_id in self.active_connections:
            if websocket is None or self.active_connections.get(client_id) is websocket:
                del self.active_connections[client_id]
                set_active_ws_connections(len(self.active_connections))

    async def send_json(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(json.dumps(message, ensure_ascii=False))


manager = ConnectionManager()


def _ensure_session_and_record_user_message(
    session_id: str,
    user_id: str,
    user_message: str,
    enforce_owner: bool = False,
) -> List[BaseMessage]:
    """Ensures ChatSession exists in DB, writes user ChatMessage,

    and loads prior conversation history as LangChain BaseMessage objects.
    """
    history_messages: List[BaseMessage] = []
    try:
        with SessionLocal() as db:
            session = (
                db.query(ChatSession)
                .filter(ChatSession.session_id == session_id, ChatSession.is_deleted == False)  # noqa: E712
                .first()
            )
            if session and enforce_owner and session.user_id != user_id:
                raise PermissionError("无权访问或修改其他用户的对话会话")
            if not session:
                title = user_message[:30].strip() or "新对话"
                session = ChatSession(
                    session_id=session_id,
                    user_id=user_id,
                    title=title,
                )
                db.add(session)
                db.commit()

            # Load prior messages for multi-turn conversational context (limit 20)
            prior_records = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(20)
                .all()
            )
            prior_records.reverse()

            for rec in prior_records:
                if rec.role == "user":
                    history_messages.append(HumanMessage(content=rec.content))
                elif rec.role == "assistant":
                    history_messages.append(AIMessage(content=rec.content))

            # Record current user turn
            user_msg_record = ChatMessage(
                session_id=session_id,
                role="user",
                content=user_message,
            )
            db.add(user_msg_record)
            session.updated_at = datetime.utcnow()
            db.commit()

    except PermissionError:
        raise
    except Exception as e:
        logger.warning(f"[ChatWS] Failed to persist user message to DB: {e}")

    # Append current message to state
    history_messages.append(HumanMessage(content=user_message))
    return history_messages


def _record_assistant_message(
    session_id: str,
    assistant_message: str,
    sources: Optional[str] = None,
    thought: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    thought_steps: Optional[str] = None,
) -> None:
    """Persists assistant completion message, full thought trace, and duration to database."""
    if not assistant_message:
        return
    try:
        with SessionLocal() as db:
            assistant_record = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=assistant_message,
                sources=sources,
                thought=thought,
                duration_seconds=duration_seconds,
                thought_steps=thought_steps,
            )
            db.add(assistant_record)

            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if session:
                session.updated_at = datetime.utcnow()

            db.commit()
    except Exception as e:
        logger.warning(f"[ChatWS] Failed to persist assistant response to DB: {e}")


def strip_internal_answer_tags(text: str) -> str:
    """Strips internal architectural debugging tags like [Chat Answer]: or [RAG Answer]: from user-facing text."""
    if not text or not isinstance(text, str):
        return text
    cleaned = re.sub(r"^\[(?:Chat|RAG|Tool)\s*Answer\]:\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Hello!\s*I have processed your message:\s*['\"].*?['\"]\.\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


async def safe_send_json(websocket: WebSocket, payload: dict) -> bool:
    """Safely transmits JSON over WebSocket, preventing RuntimeError if socket has already closed."""
    try:
        if websocket.client_state != WebSocketState.CONNECTED:
            return False
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))
        return True
    except (RuntimeError, WebSocketDisconnect):
        return False
    except Exception as e:
        logger.debug(f"[ChatWS] safe_send_json failed: {e}")
        return False


async def process_ws_chat_stream(
    websocket: WebSocket,
    client_id: str,
    data: dict,
    authenticated_user: Optional[UserPayload] = None,
):
    """Processes chat request over WebSocket and streams events in real-time."""
    user_message = data.get("message", "").strip()
    thread_id = data.get("thread_id", f"ws_thread_{client_id}")
    user_id = authenticated_user.username if authenticated_user else data.get("user_id", "u_ws_default")
    session_id = data.get("session_id", f"s_ws_{client_id}")
    metadata = (data.get("metadata") or {}).copy()
    metadata["thread_id"] = thread_id
    metadata["session_id"] = session_id
    if authenticated_user is not None:
        metadata["user_role"] = authenticated_user.role.value
        metadata["department"] = authenticated_user.department
        metadata["display_name"] = authenticated_user.display_name

    # 0. Input Security & Guardrail Check (OWASP LLM01 Prompt Injection / Jailbreak)
    guard_result = validate_input(user_message)
    if not guard_result.is_valid:
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "status": 400,
                "thread_id": thread_id,
                "session_id": session_id,
                "message": f"400 Bad Request: Policy Violation - {guard_result.reason} ({guard_result.category})",
                "category": guard_result.category,
            },
        )
        return

    # 1. Database Persistence: Ensure session & persist user message with multi-turn history
    try:
        full_conversation_messages = _ensure_session_and_record_user_message(
            session_id=session_id,
            user_id=user_id,
            user_message=user_message,
            enforce_owner=authenticated_user is not None,
        )
    except PermissionError as perm_err:
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "status": 403,
                "thread_id": thread_id,
                "session_id": session_id,
                "message": str(perm_err),
            },
        )
        return

    initial_state: AgentState = {
        "messages": full_conversation_messages,
        "user_id": user_id,
        "session_id": session_id,
        "current_step": "init",
        "intent": "",
        "secondary_intent": "",
        "context": [],
        "metadata": metadata,
    }
    config = {"configurable": {"thread_id": thread_id}}

    # Initialize streaming PII sanitizer & timing telemetry
    sanitizer = StreamingSanitizer()
    import time
    stream_start_time = time.time()
    first_token_time: Optional[float] = None
    ttft_recorded = False
    streamed_thought_chunks: List[str] = []
    thought_steps_history: List[str] = []

    # Send Initial Handshake Response
    await safe_send_json(
        websocket,
        {
            "type": "start",
            "thread_id": thread_id,
            "session_id": session_id,
            "status": "PROCESSING",
        },
    )

    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            kind = event.get("event")
            name = event.get("name", "")

            # 1. Node Execution Transition Events
            if kind == "on_chain_start" and name in ["router", "retrieve", "tool", "approval", "generate"]:
                step_mapping = {
                    "router": "意图理解与业务范畴分析",
                    "retrieve": "调取企业规章与制度知识库",
                    "tool": "核验业务系统实时数据",
                    "approval": "生成人机协同审批确认单据",
                    "generate": "依据核验条款组织回复建议",
                }
                title = step_mapping.get(name, f"正在执行 {name} 节点...")
                if title not in thought_steps_history:
                    thought_steps_history.append(title)
                if not await safe_send_json(
                    websocket,
                    {
                        "type": "node_start",
                        "node": name,
                        "title": title,
                        "thread_id": thread_id,
                        "session_id": session_id,
                    },
                ):
                    break

            # 1.1 Retrieval and Rerank Completion Trace
            elif kind == "on_chain_end" and name == "retrieve":
                output = event.get("data", {}).get("output", {})
                context = output.get("context", []) if isinstance(output, dict) else []
                if context:
                    top_doc = context[0]
                    meta = top_doc.get("metadata", {})
                    doc_name = meta.get("filename") or meta.get("source") or meta.get("title") or "企业制度指南"
                    doc_name = doc_name.replace("\\", "/").split("/")[-1]
                    score = meta.get("rerank_score") or meta.get("score")
                    score_text = f" (置信度: {score})" if score is not None else ""
                    rerank_step_title = f"语义重排并匹配核心条款 (匹配《{doc_name}》{score_text})"
                    if rerank_step_title not in thought_steps_history:
                        thought_steps_history.append(rerank_step_title)
                    await safe_send_json(
                        websocket,
                        {
                            "type": "thought_step",
                            "step": "rerank",
                            "title": rerank_step_title,
                            "thread_id": thread_id,
                            "session_id": session_id,
                        },
                    )
                    # Push confirmed knowledge sources to frontend
                    sources_list = []
                    for idx, d in enumerate(context[:5], 1):
                        d_meta = d.get("metadata", {})
                        d_title = d_meta.get("filename") or d_meta.get("title") or f"制度文档 {idx}"
                        d_title = d_title.replace("\\", "/").split("/")[-1]
                        d_snippet = d.get("content", "").strip()[:180]
                        sources_list.append({
                            "doc_id": f"SOP-2026-0{idx}",
                            "title": f"《{d_title}》",
                            "snippet": d_snippet,
                            "tag": d_meta.get("category", "制度条款"),
                        })
                    await safe_send_json(
                        websocket,
                        {
                            "type": "sources",
                            "sources": sources_list,
                            "thread_id": thread_id,
                            "session_id": session_id,
                        },
                    )

            # 2. LLM Streaming Tokens
            elif kind == "on_chat_model_stream":
                # Isolate internal router LLM calls so internal JSON never leaks into WS stream or TTFT
                event_meta = event.get("metadata") or {}
                event_tags = event.get("tags") or []
                if (
                    event_meta.get("langgraph_node") == "router"
                    or "internal_router" in event_tags
                ):
                    continue
                # Deduplicate nested ChatOpenAI / EnterpriseChatOpenAI / NativeOllamaChatModel stream events when wrapped in ResilientChatModel
                if event.get("name") in ["ChatOpenAI", "EnterpriseChatOpenAI", "NativeOllamaChatModel"]:
                    continue
                chunk = event.get("data", {}).get("chunk")

                # Transmit reasoning/thought token if generated by thinking models (Ollama/DeepSeek)
                if chunk and hasattr(chunk, "additional_kwargs"):
                    reasoning_token = chunk.additional_kwargs.get("reasoning_content") or chunk.additional_kwargs.get("reasoning")
                    if reasoning_token:
                        streamed_thought_chunks.append(reasoning_token)
                        await safe_send_json(
                            websocket,
                            {
                                "type": "thought",
                                "content": reasoning_token,
                                "thread_id": thread_id,
                                "session_id": session_id,
                            },
                        )

                if chunk and hasattr(chunk, "content") and chunk.content:
                    if first_token_time is None:
                        first_token_time = time.time()
                    if not ttft_recorded:
                        record_ttft(max(0.0, first_token_time - stream_start_time))
                        ttft_recorded = True
                    safe_token = sanitizer.process_chunk(chunk.content)
                    if safe_token:
                        if not await safe_send_json(
                            websocket,
                            {
                                "type": "token",
                                "content": safe_token,
                                "thread_id": thread_id,
                                "session_id": session_id,
                            },
                        ):
                            break

            # 3. Tool Execution Logs
            elif kind == "on_tool_start":
                tool_name = event.get("name")
                tool_input = event.get("data", {}).get("input")
                await safe_send_json(
                    websocket,
                    {
                        "type": "tool_log",
                        "status": "started",
                        "tool": tool_name,
                        "input": tool_input,
                        "thread_id": thread_id,
                        "session_id": session_id,
                    },
                )

            elif kind == "on_tool_end":
                tool_name = event.get("name")
                tool_output = event.get("data", {}).get("output")
                await safe_send_json(
                    websocket,
                    {
                        "type": "tool_log",
                        "status": "completed",
                        "tool": tool_name,
                        "output": sanitize_text(str(tool_output)),
                        "thread_id": thread_id,
                        "session_id": session_id,
                    },
                )

        # Flush any remaining tokens from streaming sanitizer buffer
        flush_token = sanitizer.flush()
        if flush_token:
            await safe_send_json(
                websocket,
                {
                    "type": "token",
                    "content": flush_token,
                    "thread_id": thread_id,
                    "session_id": session_id,
                },
            )

    except GraphInterrupt:
        # LangGraph Interrupt Caught (e.g. High-value Purchase Approval required)
        pass
    except asyncio.CancelledError:
        await safe_send_json(
            websocket,
            {
                "type": "cancelled",
                "thread_id": thread_id,
                "session_id": session_id,
                "message": "Chat generation cancelled by user",
            },
        )
        return
    except Exception as e:
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "thread_id": thread_id,
                "session_id": session_id,
                "message": str(e),
            },
        )
        return

    # Check Graph State Post-Stream for Interrupt or Final Result
    state_snapshot = graph.get_state(config)
    if state_snapshot and state_snapshot.next == ("approval",):
        # State paused at approval_node interrupt()
        interrupt_val = {}
        if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
            interrupt_val = state_snapshot.tasks[0].interrupts[0].value

        await safe_send_json(
            websocket,
            {
                "type": "interrupt",
                "thread_id": thread_id,
                "session_id": session_id,
                "approval_data": interrupt_val,
            },
        )
    else:
        # State completed
        final_values = state_snapshot.values if state_snapshot else {}
        messages = final_values.get("messages", [])
        last_text = messages[-1].content if messages else ""
        sanitized_answer = strip_internal_answer_tags(sanitize_text(last_text))

        # Extract sources from context if available
        context_docs = final_values.get("context", [])
        sources_str = None
        if context_docs:
            source_list = [
                doc.get("metadata", {}).get("filename") or doc.get("metadata", {}).get("source", "Doc")
                for doc in context_docs
                if isinstance(doc, dict)
            ]
            if source_list:
                sources_str = json.dumps(list(set(source_list)), ensure_ascii=False)

        # Calculate actual thinking duration & assemble thought trace for persistence
        elapsed_sec = round(first_token_time - stream_start_time, 1) if first_token_time else round(time.time() - stream_start_time, 1)
        if not ttft_recorded:
            record_ttft(max(0.0, (first_token_time or time.time()) - stream_start_time))
            ttft_recorded = True
        persisted_thought = "".join(streamed_thought_chunks).strip() if streamed_thought_chunks else None
        persisted_steps = json.dumps(thought_steps_history, ensure_ascii=False) if thought_steps_history else None

        # Persist assistant answer to database
        _record_assistant_message(
            session_id=session_id,
            assistant_message=sanitized_answer,
            sources=sources_str,
            thought=persisted_thought,
            duration_seconds=elapsed_sec,
            thought_steps=persisted_steps,
        )

        await safe_send_json(
            websocket,
            {
                "type": "complete",
                "thread_id": thread_id,
                "session_id": session_id,
                "final_answer": sanitized_answer,
                "current_step": final_values.get("current_step", "completed"),
            },
        )


def _resolve_ws_authenticated_user(websocket: WebSocket, token: Optional[str]) -> Optional[UserPayload]:
    """Resolves optional JWT user from query param (?token=) or Authorization header."""
    raw_token = token
    if not raw_token:
        auth_header = websocket.headers.get("authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                raw_token = parts[1]
            else:
                raise AuthenticationError("Invalid Authorization header format")

    if not raw_token:
        return None
    return resolve_user_from_token(raw_token)


@router.websocket("/ws/chat/{client_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    client_id: str,
    token: Optional[str] = Query(None),
):
    """WebSocket endpoint for duplex streaming chat."""
    authenticated_user: Optional[UserPayload] = None
    try:
        authenticated_user = _resolve_ws_authenticated_user(websocket, token)
    except AuthenticationError as auth_err:
        await websocket.accept()
        await safe_send_json(
            websocket,
            {
                "type": "error",
                "status": 401,
                "message": f"身份凭证无效或已过期，请重新登录 ({auth_err.message})",
            },
        )
        await websocket.close(code=4401)
        return

    await manager.connect(client_id, websocket)
    active_stream_task: Optional[asyncio.Task] = None
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await safe_send_json(websocket, {"type": "error", "message": "Invalid JSON format"})
                continue

            # 1. Heartbeat ping: instant pong response without invoking LLM
            if data.get("type") == "ping":
                await safe_send_json(websocket, {"type": "pong", "timestamp": data.get("timestamp")})
                continue

            # 2. Ignore empty message payloads
            user_msg = data.get("message", "").strip()
            if not user_msg:
                continue

            thread_id = data.get("thread_id", f"ws_thread_{client_id}")

            # 3. If previous generation task is still running, safely cancel it before starting new one
            if active_stream_task and not active_stream_task.done():
                active_stream_task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(active_stream_task), timeout=0.2)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            # 4. Spawn independent worker task so main receive loop stays active
            active_stream_task = asyncio.create_task(
                process_ws_chat_stream(websocket, client_id, data, authenticated_user=authenticated_user)
            )
            if thread_id:
                task_manager.register_task(thread_id, active_stream_task)

            # Cleanup task upon completion
            def _cleanup_callback(fut: asyncio.Future, t_id: str = thread_id):
                if t_id:
                    task_manager.unregister_task(t_id)

            active_stream_task.add_done_callback(_cleanup_callback)

    except WebSocketDisconnect:
        if active_stream_task and not active_stream_task.done():
            active_stream_task.cancel()
    except Exception as exc:
        logger.error(f"[ChatWS] Unexpected WebSocket error for client '{client_id}': {exc}", exc_info=True)
        if active_stream_task and not active_stream_task.done():
            active_stream_task.cancel()
    finally:
        manager.disconnect(client_id, websocket)
