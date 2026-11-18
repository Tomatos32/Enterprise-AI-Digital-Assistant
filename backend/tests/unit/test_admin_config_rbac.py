"""Unit Tests for Issue-0057: Admin Config Control Plane, RBAC, Secret Masking & Hot-Reload."""

import importlib
import json
import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

import backend.api.v1.admin_config as admin_config_api
import backend.core.runtime_config as runtime_config_module
import backend.rag.retriever as retriever_module
from backend.core.config import settings
from backend.core.llm import (
    EnterpriseChatOpenAI,
    LocalEnterpriseChatModel,
    NativeOllamaChatModel,
    ResilientChatModel,
    get_chat_llm,
    get_llm_info,
)
from backend.graph.state import AgentState
from backend.main import app

generate_node_module = importlib.import_module("backend.graph.nodes.generate_node")
retrieve_node_module = importlib.import_module("backend.graph.nodes.retrieve_node")
knowledge_tools_module = importlib.import_module("backend.tools.impl.knowledge_tools")


@pytest.fixture(autouse=True)
def isolated_runtime_config(tmp_path, monkeypatch):
    """Isolates persisted runtime_config.json and baseline Settings across tests."""
    temp_cfg_file = tmp_path / "runtime_config.json"
    monkeypatch.setattr(runtime_config_module, "RUNTIME_CONFIG_PATH", temp_cfg_file)
    orig_api_key = settings.LLM_API_KEY
    orig_secret_key = settings.SECRET_KEY
    runtime_config_module.reset_runtime_config(updated_by="test_setup")
    yield temp_cfg_file
    settings.LLM_API_KEY = orig_api_key
    settings.SECRET_KEY = orig_secret_key
    runtime_config_module.reset_runtime_config(updated_by="test_teardown")


@pytest.fixture
def client():
    return TestClient(app)


def _auth_header_for(client: TestClient, username: str) -> dict:
    resp = client.post("/api/v1/auth/switch-role", json={"username": username})
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_config_endpoints_require_admin_role(client):
    """Verifies 401 when unauthenticated and 403 for employee and manager across all admin endpoints."""
    endpoints = [
        ("GET", "/api/v1/admin/config", None),
        ("PUT", "/api/v1/admin/config", {"llm_thinking": True}),
        ("POST", "/api/v1/admin/config/reset", None),
        ("POST", "/api/v1/admin/config/probe", {"llm_provider": "local_fallback"}),
    ]

    # 1. Missing token -> 401
    for method, url, body in endpoints:
        resp = client.request(method, url, json=body)
        assert resp.status_code == 401, f"Expected 401 for unauthenticated {method} {url}"

    # 2. Employee & Manager -> 403
    for role_user in ("employee", "manager"):
        headers = _auth_header_for(client, role_user)
        for method, url, body in endpoints:
            resp = client.request(method, url, json=body, headers=headers)
            assert resp.status_code == 403, f"Expected 403 for {role_user} on {method} {url}"

    # 3. Admin -> 200
    admin_headers = _auth_header_for(client, "admin")
    resp = client.get("/api/v1/admin/config", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 200


def test_admin_config_secret_masking_and_whitelist_protection(client, isolated_runtime_config):
    """Ensures plaintext LLM_API_KEY and SECRET_KEY are never returned or persisted, and non-whitelist keys are ignored."""
    settings.LLM_API_KEY = "sk-super-secret-live-key-9876"
    original_secret_key = settings.SECRET_KEY
    admin_headers = _auth_header_for(client, "admin")

    # 1. GET never exposes plaintext secrets
    get_resp = client.get("/api/v1/admin/config", headers=admin_headers)
    assert get_resp.status_code == 200
    raw_get_text = get_resp.text
    assert "sk-super-secret-live-key-9876" not in raw_get_text
    assert original_secret_key not in raw_get_text
    data = get_resp.json()["data"]
    assert data["api_key_configured"] is True
    assert data["api_key_masked"] == "sk-****9876"
    assert data["jwt_secret_configured"] is True

    # 2. PUT ignores non-whitelist fields and preserves key if masked or blank is submitted
    put_resp = client.put(
        "/api/v1/admin/config",
        json={
            "llm_model": "qwen3.5:2b",
            "llm_api_key": "sk-****9876",
            "SECRET_KEY": "tampered_secret",
            "secret_key": "tampered_secret",
            "MYSQL_PASSWORD": "hacked_password",
        },
        headers=admin_headers,
    )
    assert put_resp.status_code == 200
    assert settings.SECRET_KEY == original_secret_key
    assert settings.LLM_API_KEY == "sk-super-secret-live-key-9876"
    assert "sk-super-secret-live-key-9876" not in put_resp.text
    assert original_secret_key not in put_resp.text

    # Persisted JSON must only hold non-secret whitelisted fields
    assert isolated_runtime_config.exists()
    persisted = json.loads(isolated_runtime_config.read_text(encoding="utf-8"))
    assert "llm_api_key" not in persisted
    assert "SECRET_KEY" not in persisted
    assert persisted["llm_model"] == "qwen3.5:2b"

    # 3. Write-only API key update updates memory key without returning plaintext
    key_update_resp = client.put(
        "/api/v1/admin/config",
        json={"llm_api_key": "sk-new-rotated-secret-4321"},
        headers=admin_headers,
    )
    assert key_update_resp.status_code == 200
    assert settings.LLM_API_KEY == "sk-new-rotated-secret-4321"
    assert "sk-new-rotated-secret-4321" not in key_update_resp.text
    assert key_update_resp.json()["data"]["api_key_masked"] == "sk-****4321"

    # 4. Explicit clear_api_key clears in-memory API key
    clear_resp = client.put(
        "/api/v1/admin/config",
        json={"clear_api_key": True},
        headers=admin_headers,
    )
    assert clear_resp.status_code == 200
    assert settings.LLM_API_KEY is None
    assert clear_resp.json()["data"]["api_key_configured"] is False
    assert clear_resp.json()["data"]["api_key_masked"] == "未配置"


def test_admin_config_validation_rejects_invalid_bounds(client):
    """Validates Pydantic boundary enforcement on temperature, max_tokens, top_k, min_score, and api_base."""
    admin_headers = _auth_header_for(client, "admin")

    invalid_payloads = [
        {"llm_temperature": 2.5},
        {"llm_max_tokens": 32},
        {"rag_top_k": 50},
        {"rag_min_score": 1.2},
        {"llm_provider": "unsupported_engine"},
        {"llm_api_base": "ftp://invalid.example.com"},
        {"llm_model": "   "},
    ]

    for payload in invalid_payloads:
        resp = client.put("/api/v1/admin/config", json=payload, headers=admin_headers)
        assert resp.status_code in (400, 422), f"Expected validation failure for {payload}"


def test_admin_config_hot_reload_wires_llm_and_retriever(client, monkeypatch, isolated_runtime_config):
    """Verifies PUT updates immediately propagate to get_llm_info, get_chat_llm, and HybridRetriever."""
    admin_headers = _auth_header_for(client, "admin")

    put_resp = client.put(
        "/api/v1/admin/config",
        json={
            "llm_provider": "ollama",
            "llm_model": "qwen3.5:2b",
            "llm_api_base": "http://127.0.0.1:11434",
            "llm_thinking": True,
            "llm_temperature": 0.65,
            "llm_max_tokens": 2048,
            "rag_top_k": 5,
            "rag_min_score": 0.32,
            "system_prompt_instruction": "回答末尾补充合规核对提示。",
        },
        headers=admin_headers,
    )
    assert put_resp.status_code == 200

    # 1. LLM telemetry & factory reflect live runtime overrides
    info = get_llm_info()
    assert info["provider"] == "ollama"
    assert info["model"] == "qwen3.5:2b"
    assert info["thinking"] is True
    assert info["temperature"] == 0.65
    assert info["max_tokens"] == 2048
    assert info["active_engine"] == "NativeOllamaChatModel"

    llm = get_chat_llm()
    assert isinstance(llm, ResilientChatModel)
    assert isinstance(llm.primary_model, NativeOllamaChatModel)
    assert llm.primary_model.model_name == "qwen3.5:2b"
    assert llm.primary_model.think is True
    assert llm.primary_model.temperature == 0.65
    assert llm.primary_model.max_tokens == 2048

    # Also verify DeepSeek / ChatOpenAI preset wiring
    ds_resp = client.put(
        "/api/v1/admin/config",
        json={
            "llm_provider": "deepseek",
            "llm_model": "deepseek-chat",
            "llm_api_base": "",
            "llm_temperature": 0.35,
            "llm_max_tokens": 1024,
        },
        headers=admin_headers,
    )
    assert ds_resp.status_code == 200
    assert get_llm_info()["active_engine"] == "ChatOpenAI"
    ds_llm = get_chat_llm()
    assert isinstance(ds_llm, ResilientChatModel)
    assert isinstance(ds_llm.primary_model, EnterpriseChatOpenAI)
    assert ds_llm.primary_model.model_name == "deepseek-chat"
    assert ds_llm.primary_model.temperature == 0.35
    assert ds_llm.primary_model.max_tokens == 1024
    assert ds_llm.primary_model.openai_api_base == "https://api.deepseek.com/v1"

    # Re-apply ollama & RAG params before retriever check
    assert client.put(
        "/api/v1/admin/config",
        json={"rag_top_k": 5, "rag_min_score": 0.32},
        headers=admin_headers,
    ).status_code == 200

    # 2. HybridRetriever uses runtime top_k/min_score by default while honoring explicit overrides
    captured_rerank_calls = []

    class DummyReranker:
        def rerank(self, query, docs, top_k=5, min_score=None, relative_threshold=None, primary_domain=None):
            captured_rerank_calls.append({"top_k": top_k, "min_score": min_score})
            return docs[:top_k]

    sample_docs = [
        Document(page_content=f"制度条款 {i}", metadata={"filename": f"doc_{i}.md", "category": "FINANCE"})
        for i in range(6)
    ]
    monkeypatch.setattr(retriever_module, "search_similar_documents", lambda **kwargs: sample_docs)
    monkeypatch.setattr(retriever_module, "Reranker", DummyReranker)

    retriever = retriever_module.HybridRetriever.__new__(retriever_module.HybridRetriever)
    retriever.bm25_retriever = type("DummyBM25", (), {"search": lambda self, **kwargs: []})()
    retriever.sample_docs = sample_docs

    docs_default = retriever.retrieve(query="差旅费标准")
    assert len(docs_default) == 5
    assert captured_rerank_calls[-1] == {"top_k": 5, "min_score": 0.32}

    docs_explicit = retriever.retrieve(query="差旅费标准", top_k=2, min_score=0.5)
    assert len(docs_explicit) == 2
    assert captured_rerank_calls[-1] == {"top_k": 2, "min_score": 0.5}

    # 3. Reset restores baseline defaults and removes persisted file
    reset_resp = client.post("/api/v1/admin/config/reset", headers=admin_headers)
    assert reset_resp.status_code == 200
    assert not isolated_runtime_config.exists()
    reset_data = reset_resp.json()["data"]
    assert reset_data["rag_top_k"] == 3
    assert reset_data["rag_min_score"] == 0.16
    assert reset_data["system_prompt_instruction"] == ""


@pytest.mark.asyncio
async def test_generate_node_injects_admin_instruction_and_local_fallback_stays_clean(client, monkeypatch):
    """Verifies generate_node injects system_prompt_instruction and LocalEnterpriseChatModel does not leak it into citations."""
    admin_headers = _auth_header_for(client, "admin")
    instruction_text = "凡涉及报销金额，务必使用加粗表格标明职级上限。"

    resp = client.put(
        "/api/v1/admin/config",
        json={
            "llm_provider": "local_fallback",
            "rag_min_score": 0.25,
            "system_prompt_instruction": instruction_text,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200

    captured_system_prompts = []

    class CapturingLLM:
        async def ainvoke(self, messages):
            captured_system_prompts.append(messages[0].content)
            # Also validate LocalEnterpriseChatModel ignores appended admin policy footer when synthesizing RAG snippet
            fallback_ans = LocalEnterpriseChatModel()._synthesize_response(messages)
            assert instruction_text not in fallback_ans
            return AIMessage(content=fallback_ans)

    monkeypatch.setattr(generate_node_module, "get_chat_llm", lambda: CapturingLLM())

    state: AgentState = {
        "messages": [HumanMessage(content="出差住宿报销标准是多少？")],
        "user_id": "employee",
        "session_id": "s_admin_cfg_test",
        "intent": "retrieve",
        "context": [
            {
                "content": "一线城市住宿费报销上限为 600 元/晚。",
                "metadata": {
                    "filename": "01_FINANCE_TRAVEL_POLICY.md",
                    "rerank_score": 0.88,
                },
            }
        ],
        "metadata": {},
    }

    result = await generate_node_module.generate_node(state)
    assert captured_system_prompts
    assert instruction_text in captured_system_prompts[0]
    assert "[RAG Answer]" in result["messages"][0].content
    assert "600" in result["messages"][0].content


def test_admin_config_probe_local_fallback_and_mocked_ollama(client, monkeypatch):
    """Tests connectivity probe in deterministic offline mode and mocked Ollama healthy/fallback paths."""
    admin_headers = _auth_header_for(client, "admin")

    # 1. Local fallback deterministic readiness
    probe_local = client.post(
        "/api/v1/admin/config/probe",
        json={"llm_provider": "local_fallback", "llm_model": "local-enterprise-agent-v1"},
        headers=admin_headers,
    )
    assert probe_local.status_code == 200
    local_data = probe_local.json()["data"]
    assert local_data["reachable"] is True
    assert local_data["status"] == "READY"
    assert "rag_points" in local_data

    # 2. Mocked Ollama healthy probe
    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def json(self):
            return {"models": [{"name": "qwen3.5:2b"}, {"name": "qwen2.5:7b"}]}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            return FakeResponse()

    monkeypatch.setattr(admin_config_api.httpx, "AsyncClient", FakeAsyncClient)

    probe_ollama = client.post(
        "/api/v1/admin/config/probe",
        json={
            "llm_provider": "ollama",
            "llm_model": "qwen3.5:2b",
            "llm_api_base": "http://127.0.0.1:11434",
            "llm_thinking": False,
        },
        headers=admin_headers,
    )
    assert probe_ollama.status_code == 200
    ollama_data = probe_ollama.json()["data"]
    assert ollama_data["reachable"] is True
    assert ollama_data["status"] == "HEALTHY"
    assert "qwen3.5:2b" in ollama_data["available_models"]

    # 3. Auto provider with saved API key & blank api_base resolves to OpenAI default without leaking key
    settings.LLM_API_KEY = "sk-probe-secret-9999"
    captured_probe_urls = []

    class AuthErrorResponse:
        status_code = 401
        headers = {"content-type": "application/json"}

        def json(self):
            return {}

    class CapturingAsyncClient(FakeAsyncClient):
        async def get(self, url, headers=None):
            captured_probe_urls.append(url)
            return AuthErrorResponse()

    monkeypatch.setattr(admin_config_api.httpx, "AsyncClient", CapturingAsyncClient)
    probe_auto = client.post(
        "/api/v1/admin/config/probe",
        json={"llm_provider": "auto", "llm_model": "gpt-4o-mini", "llm_api_base": ""},
        headers=admin_headers,
    )
    assert probe_auto.status_code == 200
    assert captured_probe_urls == ["https://api.openai.com/v1/models"]
    auto_data = probe_auto.json()["data"]
    assert auto_data["status"] == "AUTH_ERROR"
    assert auto_data["endpoint"] == "https://api.openai.com/v1"
    assert "sk-probe-secret-9999" not in probe_auto.text


@pytest.mark.asyncio
async def test_retrieve_node_and_knowledge_tool_read_runtime_config(client, monkeypatch):
    """Ensures retrieve_node passes runtime rag_top_k/rag_min_score and search_knowledge_base honors overrides."""
    admin_headers = _auth_header_for(client, "admin")
    resp = client.put(
        "/api/v1/admin/config",
        json={"rag_top_k": 7, "rag_min_score": 0.42},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    captured_calls = []

    class FakeRetriever:
        def retrieve(self, **kwargs):
            captured_calls.append(kwargs)
            return [
                Document(
                    page_content="出差报销须在 15 个工作日内提交。",
                    metadata={"filename": "01_FINANCE_TRAVEL_POLICY.md", "rerank_score": 0.91},
                )
            ]

    monkeypatch.setattr(retrieve_node_module, "get_hybrid_retriever", lambda **kwargs: FakeRetriever())
    monkeypatch.setattr(knowledge_tools_module, "get_hybrid_retriever", lambda **kwargs: FakeRetriever())
    monkeypatch.setattr(
        retrieve_node_module.default_enterprise_kg,
        "query_graph_rag",
        lambda **kwargs: {"triples_count": 0},
    )

    state: AgentState = {
        "messages": [HumanMessage(content="出差报销时限要求")],
        "user_id": "employee",
        "session_id": "s_retrieve_cfg_test",
        "metadata": {},
    }
    node_res = await retrieve_node_module.retrieve_node(state)
    assert len(node_res["context"]) == 1
    assert captured_calls[-1]["top_k"] == 7
    assert captured_calls[-1]["min_score"] == 0.42

    # Tool default omits top_k (passes None -> resolved inside HybridRetriever), explicit overrides cleanly
    tool_default = knowledge_tools_module.search_knowledge_base(query="报销")
    assert tool_default["count"] == 1
    assert captured_calls[-1]["top_k"] is None

    tool_explicit = knowledge_tools_module.search_knowledge_base(query="报销", top_k=2)
    assert tool_explicit["count"] == 1
    assert captured_calls[-1]["top_k"] == 2

