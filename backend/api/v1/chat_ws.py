"""WebSocket Duplex Streaming Route for Enterprise AI Digital Assistant."""

import json
import asyncio
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphInterrupt

from backend.graph.workflow import graph
from backend.graph.state import AgentState
from backend.core.task_manager import task_manager

router = APIRouter(prefix="", tags=["WebSocket Chat"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_json(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(json.dumps(message, ensure_ascii=False))


manager = ConnectionManager()


async def process_ws_chat_stream(websocket: WebSocket, client_id: str, data: dict):
    """Processes chat request over WebSocket and streams events in real-time."""
    user_message = data.get("message", "").strip()
    thread_id = data.get("thread_id", f"ws_thread_{client_id}")
    user_id = data.get("user_id", "u_ws_default")
    session_id = data.get("session_id", f"s_ws_{client_id}")
    metadata = data.get("metadata", {})
    metadata["thread_id"] = thread_id

    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
        "session_id": session_id,
        "current_step": "init",
        "metadata": metadata,
    }
    config = {"configurable": {"thread_id": thread_id}}

    # Send Initial Handshake Response
    await websocket.send_text(json.dumps({
        "type": "start",
        "thread_id": thread_id,
        "status": "PROCESSING"
    }, ensure_ascii=False))

    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            kind = event.get("event")
            name = event.get("name", "")

            # 1. Node Execution Transition Events
            if kind == "on_chain_start" and name in ["router", "retrieve", "tool", "approval", "generate"]:
                await websocket.send_text(json.dumps({
                    "type": "node_start",
                    "node": name,
                    "thread_id": thread_id
                }, ensure_ascii=False))

            # 2. LLM Streaming Tokens
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await websocket.send_text(json.dumps({
                        "type": "token",
                        "content": chunk.content,
                        "thread_id": thread_id
                    }, ensure_ascii=False))

            # 3. Tool Execution Logs
            elif kind == "on_tool_start":
                tool_name = event.get("name")
                tool_input = event.get("data", {}).get("input")
                await websocket.send_text(json.dumps({
                    "type": "tool_log",
                    "status": "started",
                    "tool": tool_name,
                    "input": tool_input,
                    "thread_id": thread_id
                }, ensure_ascii=False))

            elif kind == "on_tool_end":
                tool_name = event.get("name")
                tool_output = event.get("data", {}).get("output")
                await websocket.send_text(json.dumps({
                    "type": "tool_log",
                    "status": "completed",
                    "tool": tool_name,
                    "output": str(tool_output),
                    "thread_id": thread_id
                }, ensure_ascii=False))

    except GraphInterrupt:
        # LangGraph Interrupt Caught (e.g. High-value Purchase Approval required)
        pass
    except asyncio.CancelledError:
        await websocket.send_text(json.dumps({
            "type": "cancelled",
            "thread_id": thread_id,
            "message": "Chat generation cancelled by user"
        }, ensure_ascii=False))
        return
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "thread_id": thread_id,
            "message": str(e)
        }, ensure_ascii=False))
        return

    # Check Graph State Post-Stream for Interrupt or Final Result
    state_snapshot = graph.get_state(config)
    if state_snapshot and state_snapshot.next == ("approval",):
        # State paused at approval_node interrupt()
        interrupt_val = {}
        if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
            interrupt_val = state_snapshot.tasks[0].interrupts[0].value

        await websocket.send_text(json.dumps({
            "type": "interrupt",
            "thread_id": thread_id,
            "approval_data": interrupt_val
        }, ensure_ascii=False))
    else:
        # State completed
        final_values = state_snapshot.values if state_snapshot else {}
        messages = final_values.get("messages", [])
        last_text = messages[-1].content if messages else ""

        await websocket.send_text(json.dumps({
            "type": "complete",
            "thread_id": thread_id,
            "final_answer": last_text,
            "current_step": final_values.get("current_step", "completed")
        }, ensure_ascii=False))


@router.websocket("/ws/chat/{client_id}")
async def websocket_chat_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for duplex streaming chat."""
    await manager.connect(client_id, websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, ensure_ascii=False))
                continue

            thread_id = data.get("thread_id", f"ws_thread_{client_id}")

            # Register running task to TaskManager for abort API compatibility
            current_task = asyncio.current_task()
            if current_task and thread_id:
                task_manager.register_task(thread_id, current_task)

            await process_ws_chat_stream(websocket, client_id, data)

            if thread_id:
                task_manager.remove_task(thread_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception:
        manager.disconnect(client_id)
