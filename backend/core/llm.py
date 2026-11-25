"""Unified Large Language Model (LLM) Factory & OpenAI-Compatible Interface.

Supports:
1. DeepSeek (deepseek-chat / deepseek-reasoner)
2. 通义千问 Qwen / DashScope OpenAI compatible endpoint
3. SiliconFlow 硅基流动
4. Local vLLM / Ollama OpenAI compatible servers
5. Intelligent LocalEnterpriseChatModel fallback for zero-dependency offline runs
"""

import asyncio
import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from backend.core.config import settings

logger = logging.getLogger(__name__)


class LocalEnterpriseChatModel(BaseChatModel):
    """High-Fidelity Offline Enterprise Assistant Chat Model.

    Inherits from LangChain BaseChatModel to ensure 100% compliance with LangGraph
    StateGraph node execution and event streaming (`on_chat_model_stream`).
    Synthesizes rich domain answers based on RAG context, tool execution, and prompt rules.
    """

    model_name: str = "local-enterprise-agent-v1"
    temperature: float = 0.2
    max_tokens: int = 4096
    streaming: bool = True

    @property
    def _llm_type(self) -> str:
        return "local_enterprise_chat"

    def _synthesize_response(self, messages: List[BaseMessage]) -> str:
        """Synthesizes structured enterprise response based on prompt and context."""
        query = ""
        system_text = ""

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_text += str(msg.content) + "\n"
            elif msg.type == "human":
                query = str(msg.content)

        # Strip appended admin policy footer so fallback context/tool regex extraction stays pure
        clean_system_text = re.split(r"\n+【企业管理员附加行为规范指令】：", system_text, maxsplit=1)[0]

        # 0. Check for explicit slash commands (/help, /audit read-only summary)
        if "[Slash Command: /help]" in clean_system_text:
            return (
                "您好！我是您的企业智能助手，可以协助您高效处理以下日常业务：\n\n"
                "1. **企业规章与制度解读**：查询考勤休假、差旅报销标准、办公设备借用、信息安全及客户服务规范；\n"
                "2. **业务数据实时查询**：查询同事部门/职级/联系方式，核对办公设备与物料实时库存；\n"
                "3. **工单报修与协同通知**：快速提交 IT 运维/故障报修工单、发送业务通知邮件；\n"
                "4. **采购申请与人机协同审批**：根据金额标准自动审核小额采购或发起大额采购主管审批。\n\n"
                "**快捷交互提示**：\n"
                "- 输入 `@` 可指定参考数据源（规章制度库、业务台账或采购供应链）；\n"
                "- 输入 `/kb` 精准检索制度条款，输入 `/audit` 发起审批或查看待审进度，输入 `/help` 随时呼出本指引。"
            )

        if "[Slash Command: /audit_status]" in clean_system_text:
            match = re.search(r"\[Audit Summary\]:\s*(.*)", clean_system_text, re.DOTALL)
            audit_summary = match.group(1).strip() if match else "当前暂无待处理审批单据。"
            return f"{audit_summary}"

        # 0.5. Check for approval execution outcome (including compound retrieve -> approval)
        if "[Approval Execution Result]" in clean_system_text:
            match = re.search(r"\[Approval Execution Result\]:\s*(.*)", clean_system_text, re.DOTALL)
            approval_res = match.group(1).strip() if match else "审批流程已处理完成。"
            if "【参考制度依据】" in clean_system_text:
                cited_docs = re.findall(r"【参考制度[^】]*】《(.*?)》", clean_system_text)
                if cited_docs:
                    unique_docs = "、".join(f"《{d}》" for d in dict.fromkeys(cited_docs))
                    return f"{approval_res}\n\n【依据制度】：{unique_docs}"
            return approval_res

        # 0.8. Check for self-correction / low confidence flag
        if "[Self-Correction: Low Confidence / No Direct Match]" in clean_system_text:
            return (
                f"[RAG Answer]: 经企业现行制度知识库检索与自校验：\n\n"
                f"暂未在知识库中检索到与「{query}」直接相关的规章制度条款。\n\n"
                f"**建议处理路径**：\n"
                f"1. 如涉及具体行政或薪资人事审批，建议咨询 HR 共享服务中心（SSC）；\n"
                f"2. 如涉及重大财务付款与预算指标，请联系财务部专管员核实；\n"
                f"3. 如该事项为新增业务场景，请发起工单报送制度归口部门进行合规评估。\n\n"
                f"【依据制度】：暂无直接命中条款（系统已启动自校验反思，避免事实幻觉）"
            )

        # 1. Check for tool execution status (supports compound RAG + Tool grounding)
        if "[Tool Execution Result]" in clean_system_text:
            tool_section = clean_system_text.split("[Tool Execution Result]:", 1)[1]
            tool_section = tool_section.split("【参考制度依据】", 1)[0].strip()
            tool_res = tool_section or "操作已成功提交"
            rag_note = ""
            if "【参考制度依据】" in clean_system_text:
                cited_docs = re.findall(r"【参考制度[^】]*】《(.*?)》", clean_system_text)
                if cited_docs:
                    unique_docs = "、".join(f"《{d}》" for d in dict.fromkeys(cited_docs))
                    rag_note = f"\n\n【依据制度】：{unique_docs}"
            return (
                f"[Tool Answer]: 业务操作执行完成。\n\n"
                f"**执行结果**：\n{tool_res}\n\n"
                f"系统已记录本次调用审计流水，如有审批节点流转，您可随时在控制台查看进展。{rag_note}"
            )

        # 2. Check for RAG context in system message
        if "【参考制度依据】" in clean_system_text or "参考制度" in clean_system_text:
            match = re.search(r"【参考制度依据】：\s*(.*)", clean_system_text, re.DOTALL)
            if match and match.group(1).strip():
                raw_context = match.group(1).strip()
                # Parse doc titles and relevant lines from actual retrieved text
                doc_lines = []
                cited_docs = []
                for line in raw_context.splitlines():
                    line_s = line.strip()
                    if not line_s:
                        continue
                    if "【参考制度" in line_s and "《" in line_s:
                        t_match = re.search(r"《(.*?)》", line_s)
                        if t_match and t_match.group(1) not in cited_docs:
                            cited_docs.append(t_match.group(1))
                    elif not line_s.startswith("#") and not line_s.startswith("---"):
                        doc_lines.append(line_s)

                doc_str = "、".join(f"《{d}》" for d in cited_docs) if cited_docs else "企业规章制度库"
                body_snippet = "\n".join(doc_lines[:8])
                return (
                    f"[RAG Answer]: 根据企业权威制度（{doc_str}）相关规定：\n\n"
                    f"{body_snippet}\n\n"
                    f"【依据制度】：{doc_str}"
                )

            # Fallback if no specific reference text parsed
            return (
                f"[RAG Answer]: 根据企业制度知识库检索结果：\n\n"
                f"针对您关心的「{query}」，企业已有既定制度标准与执行细则，请严格遵循内控合规流程。\n\n"
                f"【依据制度】：企业内部合规与运营管理制度汇编"
            )

        # 3. 普通对话 (Chat Intent)
        return (
            "您好！我是企业 AI 数字员工助手。\n\n"
            "我可以协助您：\n"
            "- 检索并解读企业各项规章制度（财务报销标准、采购权限门禁、考勤休假规定等）；\n"
            "- 处理行政与IT运维工单、发起人机协同审批流；\n"
            "- 对接工作流平台与协同系统。\n\n"
            "请问有什么我可以帮您的吗？"
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        content = self._synthesize_response(messages)
        message = AIMessage(content=content)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        content = self._synthesize_response(messages)
        message = AIMessage(content=content)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Asynchronously streams response token by token to trigger on_chat_model_stream."""
        content = self._synthesize_response(messages)

        # Natural token segmentation (split by characters, punctuation, and markdown delimiters)
        tokens = re.findall(r"\[\w+ Answer\]|\n\n|\n|[，。、：；！？]|\*\*.*?\*\*|\w+|[一-龥]|\s+|[^\w\s]", content)
        if not tokens:
            tokens = [content]

        for token in tokens:
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
            if run_manager:
                await run_manager.on_llm_new_token(token, chunk=chunk)
            yield chunk
            # Micro-delay to simulate realistic neural token streaming
            await asyncio.sleep(0.005)


class EnterpriseChatOpenAI(ChatOpenAI):
    """Enterprise ChatOpenAI extension that captures reasoning / thought stream tokens.

    Ensures models emitting reasoning tokens (e.g. Ollama Qwen3.5/2.5 'reasoning' or
    DeepSeek 'reasoning_content') have them preserved in `additional_kwargs`
    rather than dropped by the standard LangChain parser.
    """

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: Optional[dict],
    ) -> Optional[ChatGenerationChunk]:
        gen_chunk = super()._convert_chunk_to_generation_chunk(
            chunk=chunk,
            default_chunk_class=default_chunk_class,
            base_generation_info=base_generation_info,
        )
        if gen_chunk and gen_chunk.message:
            choices = chunk.get("choices", []) or chunk.get("chunk", {}).get("choices", [])
            if choices and choices[0].get("delta"):
                delta = choices[0]["delta"]
                reasoning = delta.get("reasoning") or delta.get("reasoning_content")
                if reasoning:
                    gen_chunk.message.additional_kwargs["reasoning_content"] = reasoning
        return gen_chunk


class NativeOllamaChatModel(BaseChatModel):
    """High-Performance Native Ollama Chat Model supporting non-blocking think mode control."""

    model_name: str = "qwen3.5:2b"
    base_url: str = "http://127.0.0.1:11434"
    think: bool = False
    temperature: float = 0.1
    max_tokens: int = 4096
    streaming: bool = True
    request_timeout: float = 60.0

    @property
    def _llm_type(self) -> str:
        return "native_ollama_chat"

    def _build_timeout(self) -> httpx.Timeout:
        t = max(0.5, float(self.request_timeout))
        return httpx.Timeout(connect=min(5.0, t), read=t, write=min(10.0, t), pool=min(5.0, t))

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        converted = []
        for m in messages:
            role = "user"
            if isinstance(m, SystemMessage):
                role = "system"
            elif isinstance(m, AIMessage):
                role = "assistant"
            converted.append({"role": role, "content": str(m.content)})
        return converted

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "stream": False,
            "think": self.think,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        with httpx.Client(trust_env=False, timeout=self._build_timeout()) as client:
            res = client.post(f"{self.base_url}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()
            content = data.get("message", {}).get("content", "")
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "stream": False,
            "think": self.think,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        async with httpx.AsyncClient(trust_env=False, timeout=self._build_timeout()) as client:
            res = await client.post(f"{self.base_url}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()
            content = data.get("message", {}).get("content", "")
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "stream": True,
            "think": self.think,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        async with httpx.AsyncClient(trust_env=False, timeout=self._build_timeout()) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        chunk_data = json.loads(line)
                        msg_chunk = chunk_data.get("message", {})
                        content = msg_chunk.get("content", "")
                        thinking = chunk_data.get("thinking", "")
                        additional_kwargs = {}
                        if thinking:
                            additional_kwargs["reasoning_content"] = thinking
                        if content or thinking:
                            yield ChatGenerationChunk(message=AIMessageChunk(content=content, additional_kwargs=additional_kwargs))


class ResilientChatModel(BaseChatModel):
    """Resilient Chat Model with automatic fallback.

    Attempts primary remote ChatOpenAI first; if authentication or network fails,
    seamlessly self-heals by invoking LocalEnterpriseChatModel to guarantee zero service disruption.
    """

    primary_model: Optional[BaseChatModel] = None
    fallback_model: LocalEnterpriseChatModel = LocalEnterpriseChatModel()

    @property
    def _llm_type(self) -> str:
        return "resilient_chat_model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.primary_model is not None:
            try:
                msg = self.primary_model.invoke(messages, stop=stop, **kwargs)
                return ChatResult(generations=[ChatGeneration(message=msg)])
            except Exception as exc:
                logger.warning(
                    "[LLM] Primary ChatModel _generate failed: %s. Falling back to LocalEnterpriseChatModel.",
                    exc,
                )
        return self.fallback_model._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.primary_model is not None:
            try:
                msg = await self.primary_model.ainvoke(messages, stop=stop, **kwargs)
                return ChatResult(generations=[ChatGeneration(message=msg)])
            except Exception as exc:
                logger.warning(
                    "[LLM] Primary ChatModel _agenerate failed: %s. Falling back to LocalEnterpriseChatModel.",
                    exc,
                )
        return await self.fallback_model._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        if self.primary_model is not None:
            try:
                streamed = False
                async for msg_chunk in self.primary_model.astream(messages, stop=stop, **kwargs):
                    has_content = bool(msg_chunk and hasattr(msg_chunk, "content") and msg_chunk.content)
                    has_reasoning = bool(
                        msg_chunk and hasattr(msg_chunk, "additional_kwargs") and (
                            msg_chunk.additional_kwargs.get("reasoning_content") or msg_chunk.additional_kwargs.get("reasoning")
                        )
                    )
                    if has_content or has_reasoning:
                        streamed = True
                        yield ChatGenerationChunk(message=msg_chunk)
                if streamed:
                    return
            except Exception as exc:
                logger.warning(
                    "[LLM] Primary ChatModel _astream failed: %s. Falling back to LocalEnterpriseChatModel.",
                    exc,
                )

        async for gen_chunk in self.fallback_model._astream(messages, stop=stop, run_manager=run_manager, **kwargs):
            yield gen_chunk


def get_chat_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    stream: Optional[bool] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    provider: Optional[str] = None,
    max_tokens: Optional[int] = None,
    thinking: Optional[bool] = None,
) -> BaseChatModel:
    """Factory function providing configured LangChain BaseChatModel instance.

    Priority:
    1. If runtime/explicit provider is 'local_fallback': returns LocalEnterpriseChatModel.
    2. If explicit API key, API base, or remote/local provider is set (DeepSeek, OpenAI, vLLM, Ollama):
       Returns `ResilientChatModel` wrapping `NativeOllamaChatModel` or `EnterpriseChatOpenAI` with automatic fallback.
    3. Fallback:
       Returns high-fidelity `LocalEnterpriseChatModel` for self-contained, zero-cost,
       100% offline development and unit tests.
    """
    from backend.core.runtime_config import get_runtime_config

    runtime_cfg = get_runtime_config()

    effective_provider = provider or runtime_cfg.llm_provider
    effective_key = api_key if api_key is not None else settings.LLM_API_KEY
    effective_base = api_base if api_base is not None else runtime_cfg.llm_api_base
    effective_model = model or runtime_cfg.llm_model
    effective_temp = temperature if temperature is not None else runtime_cfg.llm_temperature
    effective_max_tokens = max_tokens if max_tokens is not None else runtime_cfg.llm_max_tokens
    effective_thinking = thinking if thinking is not None else runtime_cfg.llm_thinking
    effective_stream = stream if stream is not None else settings.LLM_STREAM

    if effective_provider == "local_fallback":
        logger.info("[LLM] Initializing LocalEnterpriseChatModel (Admin Forced Offline Mode)")
        return LocalEnterpriseChatModel(
            model_name="local-enterprise-agent-v1",
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            streaming=effective_stream,
        )

    # Provider preset mappings
    if effective_provider == "deepseek" and not effective_base:
        effective_base = "https://api.deepseek.com/v1"
    elif effective_provider == "ollama" and not effective_base:
        effective_base = "http://127.0.0.1:11434/v1"
    elif effective_provider == "vllm" and not effective_base:
        effective_base = "http://127.0.0.1:8000/v1"

    # Normalize localhost to 127.0.0.1 for robust Windows local loopback
    if effective_base and "localhost" in effective_base:
        effective_base = effective_base.replace("localhost", "127.0.0.1")

    # Only instantiate remote ChatOpenAI if explicit settings/parameters are configured
    if effective_key or effective_base or effective_provider in ["openai", "deepseek", "vllm", "ollama"]:
        try:
            if effective_provider == "ollama":
                native_base = effective_base.replace("/v1", "").rstrip("/") if effective_base else "http://127.0.0.1:11434"
                logger.info(
                    "[LLM] Initializing ResilientChatModel with NativeOllamaChatModel (model=%s, think=%s, max_tokens=%s, base=%s)",
                    effective_model,
                    effective_thinking,
                    effective_max_tokens,
                    native_base,
                )
                ollama_model = NativeOllamaChatModel(
                    model_name=effective_model,
                    base_url=native_base,
                    think=effective_thinking,
                    temperature=effective_temp,
                    max_tokens=effective_max_tokens,
                    streaming=effective_stream,
                )
                return ResilientChatModel(
                    primary_model=ollama_model,
                    fallback_model=LocalEnterpriseChatModel(
                        model_name="local-enterprise-agent-v1",
                        temperature=effective_temp,
                        max_tokens=effective_max_tokens,
                        streaming=effective_stream,
                    ),
                )

            logger.info(
                "[LLM] Initializing ResilientChatModel with primary ChatOpenAI (model=%s, max_tokens=%s, base_url=%s)",
                effective_model,
                effective_max_tokens,
                effective_base,
            )
            # Disable system proxy inheritance for local loopback to avoid 502 Bad Gateway from local proxy tools (e.g. Clash/V2Ray)
            is_local = any(h in (effective_base or "") for h in ["127.0.0.1", "localhost", "0.0.0.0"])
            custom_async_client = httpx.AsyncClient(
                trust_env=not is_local,
                timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
            )
            custom_sync_client = httpx.Client(
                trust_env=not is_local,
                timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
            )

            chat_openai = EnterpriseChatOpenAI(
                model=effective_model,
                api_key=SecretStr(effective_key or "ollama"),
                base_url=effective_base,
                temperature=effective_temp,
                max_completion_tokens=effective_max_tokens,
                streaming=effective_stream,
                http_async_client=custom_async_client,
                http_client=custom_sync_client,
            )
            return ResilientChatModel(
                primary_model=chat_openai,
                fallback_model=LocalEnterpriseChatModel(
                    model_name="local-enterprise-agent-v1",
                    temperature=effective_temp,
                    max_tokens=effective_max_tokens,
                    streaming=effective_stream,
                ),
            )
        except Exception as exc:
            logger.warning("[LLM] Failed to configure ChatOpenAI: %s. Using LocalEnterpriseChatModel.", exc)

    # Local fallback
    logger.info("[LLM] Initializing LocalEnterpriseChatModel (Zero-Cost Offline Streaming)")
    return LocalEnterpriseChatModel(
        model_name="local-enterprise-agent-v1",
        temperature=effective_temp,
        max_tokens=effective_max_tokens,
        streaming=effective_stream,
    )


def _build_lightweight_non_thinking_llm(
    timeout_sec: float = 2.5,
    max_tokens: int = 200,
    purpose: str = "router",
) -> Optional[BaseChatModel]:
    """Builds a fast, non-thinking, non-streaming LLM client for internal cognitive tasks.

    Returns None when running in offline/local_fallback mode so internal classifiers/rewriters
    fall back immediately to their deterministic engines with zero latency.
    """
    from backend.core.runtime_config import get_runtime_config

    runtime_cfg = get_runtime_config()
    effective_provider = runtime_cfg.llm_provider
    if effective_provider == "local_fallback":
        return None

    effective_key = settings.LLM_API_KEY
    effective_base = runtime_cfg.llm_api_base
    effective_model = runtime_cfg.llm_model

    if effective_provider == "deepseek" and not effective_base:
        effective_base = "https://api.deepseek.com/v1"
    elif effective_provider == "ollama" and not effective_base:
        effective_base = "http://127.0.0.1:11434/v1"
    elif effective_provider == "vllm" and not effective_base:
        effective_base = "http://127.0.0.1:8000/v1"

    if effective_base and "localhost" in effective_base:
        effective_base = effective_base.replace("localhost", "127.0.0.1")

    has_live_backend = bool(
        effective_key
        or effective_base
        or effective_provider in ("openai", "deepseek", "vllm", "ollama")
    )
    if not has_live_backend:
        return None

    bounded_timeout = max(0.5, float(timeout_sec))
    bounded_tokens = max(64, int(max_tokens))
    try:
        if effective_provider == "ollama":
            native_base = (
                effective_base.replace("/v1", "").rstrip("/")
                if effective_base
                else "http://127.0.0.1:11434"
            )
            return NativeOllamaChatModel(
                model_name=effective_model,
                base_url=native_base,
                think=False,
                temperature=0.0,
                max_tokens=bounded_tokens,
                streaming=False,
                request_timeout=bounded_timeout,
            )

        is_local = any(h in (effective_base or "") for h in ["127.0.0.1", "localhost", "0.0.0.0"])
        custom_async_client = httpx.AsyncClient(
            trust_env=not is_local,
            timeout=httpx.Timeout(
                connect=min(1.0, bounded_timeout),
                read=bounded_timeout,
                write=min(5.0, bounded_timeout),
                pool=min(2.0, bounded_timeout),
            ),
        )
        return ChatOpenAI(
            model=effective_model,
            api_key=SecretStr(effective_key or "ollama"),
            base_url=effective_base,
            temperature=0.0,
            max_completion_tokens=bounded_tokens,
            streaming=False,
            max_retries=0,
            http_async_client=custom_async_client,
        )
    except Exception as exc:
        logger.debug("[LLM] Unable to instantiate lightweight %s LLM: %s", purpose, exc)
        return None


def get_router_llm(timeout_sec: float = 2.5) -> Optional[BaseChatModel]:
    """Returns a fast, non-thinking, non-streaming LLM client for intent classification."""
    return _build_lightweight_non_thinking_llm(
        timeout_sec=timeout_sec,
        max_tokens=200,
        purpose="router",
    )


def get_rewriter_llm(timeout_sec: float = 2.5, max_tokens: int = 320) -> Optional[BaseChatModel]:
    """Returns a fast, non-thinking, non-streaming LLM client for contextual query rewriting."""
    return _build_lightweight_non_thinking_llm(
        timeout_sec=timeout_sec,
        max_tokens=max_tokens,
        purpose="query_rewriter",
    )


def get_llm_info() -> Dict[str, Any]:
    """Returns diagnostics and configuration telemetry for the LLM subsystem."""
    from backend.core.runtime_config import get_runtime_config, resolve_active_engine_name

    cfg = get_runtime_config()
    has_key = bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip())
    active_engine = resolve_active_engine_name(cfg)

    return {
        "provider": cfg.llm_provider,
        "model": cfg.llm_model,
        "api_base": cfg.llm_api_base or "built-in-local",
        "has_api_key": has_key,
        "thinking": cfg.llm_thinking,
        "temperature": cfg.llm_temperature,
        "max_tokens": cfg.llm_max_tokens,
        "streaming": settings.LLM_STREAM,
        "active_engine": active_engine,
    }
