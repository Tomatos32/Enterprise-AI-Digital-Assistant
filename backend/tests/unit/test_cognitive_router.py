"""Unit & Integration Tests for Sprint R-06 Issue-0060:
Hybrid Multi-Turn Cognitive Intent Router, Compound Topology & DataSource/Slash Alignment.
"""

import asyncio
import importlib
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.config import settings
import backend.db.session as db_session_module
from backend.db.session import Base
from backend.graph.nodes.router_node import (
    _extract_recent_history,
    _parse_llm_router_json,
    parse_purchase_amount,
    router_node,
)
from backend.graph.state import AgentState
from backend.graph.workflow import graph
from backend.models.approval import Approval

router_module = importlib.import_module("backend.graph.nodes.router_node")


@pytest.fixture
def disable_live_router_llm(monkeypatch):
    """Forces deterministic Tier 1 + Tier 3 execution so offline tests run deterministically."""
    monkeypatch.setattr(settings, "ROUTER_LLM_ENABLED", False)


@pytest.fixture
def isolated_sqlite_db(monkeypatch):
    """Provides an isolated in-memory SQLite SessionLocal cleanly restored after each test."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    monkeypatch.setattr(db_session_module, "SessionLocal", TestingSessionLocal)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# 1. Dynamic Amount Parser Tests
# ---------------------------------------------------------------------------


def test_parse_purchase_amount_dynamic_formats():
    """Validates Arabic, Chinese, quantity*unit_price, total override, and non-money guards."""
    assert parse_purchase_amount("申请采购一台 8000 元的笔记本") == 8000.0
    assert parse_purchase_amount("申请大额设备采购：MacBook Pro 16 1台，单价 22999 元") == 22999.0
    assert parse_purchase_amount("帮我买 2 台 3500 元的显示器") == 7000.0
    assert parse_purchase_amount("申请采购 3 台办公椅，每台 2000 元") == 6000.0
    assert parse_purchase_amount("采购两台三千元的办公电脑") == 6000.0
    assert parse_purchase_amount("申请采购一批会议设备，总价1.2万元") == 12000.0
    assert parse_purchase_amount("采购2台总价6800元的显示器") == 6800.0
    assert parse_purchase_amount("帮我采购一个 300 元的无线鼠标") == 300.0
    assert parse_purchase_amount("申请采购一台三千五百元的显示器") == 3500.0
    # Model numbers and ticket levels must NOT be misparsed as RMB amounts
    assert parse_purchase_amount("MacBook Pro 16 电脑配置说明") is None
    assert parse_purchase_amount("创建P1级工单处理2026年网关异常") is None


# ---------------------------------------------------------------------------
# 2. Policy vs Action Disambiguation & Natural Tool Detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_policy_vs_action_disambiguation(disable_live_router_llm):
    """Ensures policy questions route to retrieve while real actions route to tool/approval."""
    policy_queries = [
        "采购超过5000元需要谁审批？",
        "采购2万元需要走什么流程？",
        "P1 故障工单的响应 SLA 是多久？",
        "查询采购与审批SOP标准操作流程",
        "我想申请采购一台 8000 元的笔记本，需要谁审批？",
        "迟到十分钟扣钱吗？",
        "实习生有年假吗？",
    ]
    for q in policy_queries:
        res = await router_node(
            {
                "messages": [HumanMessage(content=q)],
                # Simulate legacy ChatContainer attaching purchase_args when query contains '采购'
                "metadata": {"purchase_args": {"item_name": "MacBook Pro 16", "quantity": 1, "unit_price": 22999.0}},
            }
        )
        assert res["intent"] == "retrieve", f"Expected retrieve for policy query: {q}, got {res}"

    # High-value dynamic purchase submissions -> approval
    approval_queries = [
        "申请采购一台 8000 元的笔记本",
        "帮我买 2 台 3500 元的显示器",
        "采购两台三千元的办公电脑",
        "申请采购一批会议设备，总价1.2万元",
    ]
    for q in approval_queries:
        res = await router_node({"messages": [HumanMessage(content=q)]})
        assert res["intent"] == "approval", f"Expected approval for: {q}, got {res}"

    # Small purchase <= 5000 RMB -> tool (create_purchase)
    small_res = await router_node({"messages": [HumanMessage(content="帮我采购一个 300 元的无线鼠标")]})
    assert small_res["intent"] == "tool"
    assert small_res["metadata"].get("tool_hint") == "create_purchase"


@pytest.mark.asyncio
async def test_natural_tool_queries_without_rigid_keywords(disable_live_router_llm):
    """Validates natural phrasing routes accurately to tool without requiring literal '员工'/'库存'."""
    cases = [
        ("张伟的电话是多少", "query_employee"),
        ("张伟的电话是多少", "query_employee"),
        ("李娜在哪个部门，联系方式是什么", "query_employee"),
        ("还有几台 MacBook 可以领", "query_inventory"),
        ("电脑蓝屏了帮我报修", "create_ticket"),
        ("服务器CPU打满了赶紧拉个单子处理", "create_ticket"),
        ("帮我发封邮件通知财务部", "send_email"),
    ]
    for q, expected_hint in cases:
        res = await router_node({"messages": [HumanMessage(content=q)]})
        assert res["intent"] == "tool", f"Expected tool for '{q}', got {res}"
        assert res["metadata"].get("tool_hint") == expected_hint


@pytest.mark.asyncio
async def test_general_chat_not_forced_into_rag(disable_live_router_llm):
    """Verifies blind len(query) >= 4 -> retrieve fallback is removed for non-policy chat."""
    chat_queries = [
        "你好，你是谁？",
        "谢谢，明白了",
        "今天心情不错，随便聊两句吧",
        "帮我把这段话翻译成英文：欢迎来到企业助手",
        "帮我润色一下这段会议纪要",
        "用Python写一个快速排序算法",
        "讲个笑话放松一下",
        "我想学一下烹饪，红烧肉怎么做？",
    ]
    for q in chat_queries:
        res = await router_node({"messages": [HumanMessage(content=q)]})
        assert res["intent"] == "chat", f"Expected chat for '{q}', got {res}"


# ---------------------------------------------------------------------------
# 3. @DataSource & /Slash Command Alignment (PromptBar Contract)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_data_source_directives_alignment(disable_live_router_llm):
    """Verifies @kb_all, @db_mysql, and @erp_sap route to retrieve, tool, and tool/approval respectively."""
    # @全量企业规章制度库 (kb_all) -> retrieve
    r_kb = await router_node(
        {
            "messages": [HumanMessage(content="一线城市住宿报销标准")],
            "metadata": {"data_source_id": "kb_all", "data_source": "全量企业规章制度库"},
        }
    )
    assert r_kb["intent"] == "retrieve"
    assert r_kb["metadata"]["resolved_data_source"] == "kb_all"

    # @MySQL 业务台账 (db_mysql) -> tool (NOT retrieve!)
    r_mysql_inv = await router_node(
        {
            "messages": [HumanMessage(content="查一下显示器余量")],
            "metadata": {"data_source_id": "db_mysql", "data_source": "MySQL 业务台账"},
        }
    )
    assert r_mysql_inv["intent"] == "tool"
    assert r_mysql_inv["metadata"]["tool_hint"] == "query_inventory"

    r_mysql_emp = await router_node(
        {
            "messages": [HumanMessage(content="查一下张伟的部门和电话")],
            "metadata": {"data_source": "MySQL 业务台账"},
        }
    )
    assert r_mysql_emp["intent"] == "tool"
    assert r_mysql_emp["metadata"]["tool_hint"] == "query_employee"

    # @ERP 采购与供应链 (erp_sap) -> tool for stock, approval for high-value purchase
    r_erp_inv = await router_node(
        {
            "messages": [HumanMessage(content="MacBook 现货情况")],
            "metadata": {"data_source_id": "erp_sap", "data_source": "ERP 采购与供应链"},
        }
    )
    assert r_erp_inv["intent"] == "tool"
    assert r_erp_inv["metadata"]["tool_hint"] == "query_inventory"

    r_erp_app = await router_node(
        {
            "messages": [HumanMessage(content="申请采购 2 台 6000 元显示器")],
            "metadata": {"data_source_id": "erp_sap", "data_source": "ERP 采购与供应链"},
        }
    )
    assert r_erp_app["intent"] == "approval"

    # Inline @MySQL prefix without popover metadata
    r_inline = await router_node({"messages": [HumanMessage(content="@MySQL业务台账 看看显示器还有多少")]})
    assert r_inline["intent"] == "tool"
    assert r_inline["metadata"]["tool_hint"] == "query_inventory"


@pytest.mark.asyncio
async def test_slash_commands_and_audit_rbac(disable_live_router_llm, isolated_sqlite_db):
    """Validates /kb, /help, /audit read-only (RBAC isolated) vs /audit purchase submission."""
    # /kb strips prefix and routes to retrieve
    r_kb = await router_node({"messages": [HumanMessage(content="/kb 差旅住宿报销标准")]})
    assert r_kb["intent"] == "retrieve"
    assert r_kb["metadata"]["normalized_query"] == "差旅住宿报销标准"
    assert r_kb["metadata"]["slash_command"] == "kb"

    # /help routes to chat with slash_command=help
    r_help = await router_node({"messages": [HumanMessage(content="/help")]})
    assert r_help["intent"] == "chat"
    assert r_help["metadata"]["slash_command"] == "help"

    help_out = await graph.ainvoke(
        {"messages": [HumanMessage(content="/help")], "metadata": {}},
        config={"configurable": {"thread_id": "thread_slash_help_0060"}},
    )
    help_text = help_out["messages"][-1].content
    assert "规章" in help_text and "/audit" in help_text
    assert "LangGraph" not in help_text and "Qdrant" not in help_text

    # /audit read-only MUST NOT trigger approval_node interrupt; enforces RBAC
    isolated_sqlite_db.add(
        Approval(
            approval_id="APP-20261124-9001",
            thread_id="t_pending_1",
            item_name="MacBook Pro 16",
            quantity=1,
            unit_price=22999.0,
            total_price=22999.0,
            department="研发部",
            reason="测试待审",
            status="PENDING",
        )
    )
    isolated_sqlite_db.commit()

    # Unauthenticated / missing role also fails closed (cannot view global pending approvals)
    anon_audit = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="/audit 查看待审流程")],
            "metadata": {},
        },
        config={"configurable": {"thread_id": "thread_audit_anon_0060"}},
    )
    assert anon_audit["intent"] == "chat"
    assert anon_audit["metadata"]["slash_command"] == "audit_status"
    assert "APP-20261124-9001" not in anon_audit["messages"][-1].content
    assert "权限" in anon_audit["messages"][-1].content

    # Employee role cannot view global pending approval queue
    emp_audit = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="/audit 查看待审流程")],
            "metadata": {"user_role": "employee"},
        },
        config={"configurable": {"thread_id": "thread_audit_emp_0060"}},
    )
    assert emp_audit["intent"] == "chat"
    assert emp_audit["metadata"]["slash_command"] == "audit_status"
    assert "APP-20261124-9001" not in emp_audit["messages"][-1].content
    assert "普通员工" in emp_audit["messages"][-1].content or "权限" in emp_audit["messages"][-1].content

    # Manager role sees pending approval summary
    mgr_audit = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="/audit")],
            "metadata": {"user_role": "manager"},
        },
        config={"configurable": {"thread_id": "thread_audit_mgr_0060"}},
    )
    assert mgr_audit["intent"] == "chat"
    assert "APP-20261124-9001" in mgr_audit["messages"][-1].content

    # /audit with explicit purchase submission routes to approval
    r_audit_submit = await router_node(
        {"messages": [HumanMessage(content="/audit 申请采购 MacBook Pro 16 1台，单价 22999 元")]}
    )
    assert r_audit_submit["intent"] == "approval"
    assert r_audit_submit["metadata"]["slash_command"] == "audit_submit"


# ---------------------------------------------------------------------------
# 4. Multi-Turn Context Window (6-Turn Inheritance & Intent Shifts)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_turn_followups_and_intent_shifts(disable_live_router_llm):
    """Tests elliptical follow-up inheritance and intent transitions over multi-turn history."""
    # 4.1 RAG policy follow-up without domain keyword
    s_rag_follow: AgentState = {
        "messages": [
            HumanMessage(content="我出差需要临时借用备用机，期限是多久"),
            AIMessage(content="[RAG Answer]: 单次临时借用备用机最长不超过 14 个自然日。【依据制度】：《03_IT_运维与资产借用指南.md》"),
            HumanMessage(content="如果超过这个天数呢"),
        ]
    }
    r1 = await router_node(s_rag_follow)
    assert r1["intent"] == "retrieve"

    # 4.2 Travel policy city follow-up
    s_city_follow: AgentState = {
        "messages": [
            HumanMessage(content="一线城市出差住宿标准是多少"),
            AIMessage(content="[RAG Answer]: 一线城市住宿标准上限为 600 元/晚。"),
            HumanMessage(content="二线城市呢？"),
        ]
    }
    r2 = await router_node(s_city_follow)
    assert r2["intent"] == "retrieve"

    # 4.3 Employee pronoun follow-up
    s_emp_follow: AgentState = {
        "messages": [
            HumanMessage(content="查询IT运维部员工张伟的岗位职级"),
            AIMessage(content="[Tool Answer]: 张伟，IT运维部，职级 P6。"),
            HumanMessage(content="再查一下他的邮箱"),
        ]
    }
    r3 = await router_node(s_emp_follow)
    assert r3["intent"] == "tool"
    assert r3["metadata"].get("tool_hint") == "query_employee"

    # 4.4 Inventory follow-up
    s_inv_follow: AgentState = {
        "messages": [
            HumanMessage(content="查一下MacBook库存还有多少"),
            AIMessage(content="[Tool Answer]: MacBook Pro 16 当前库存 5 台。"),
            HumanMessage(content="那显示器呢"),
        ]
    }
    r4 = await router_node(s_inv_follow)
    assert r4["intent"] == "tool"
    assert r4["metadata"].get("tool_hint") == "query_inventory"

    # 4.5 Intent shift: Policy inquiry -> Approval submission
    s_shift_app: AgentState = {
        "messages": [
            HumanMessage(content="申请采购一台 8000 元的笔记本需要谁审批？"),
            AIMessage(content="[RAG Answer]: 金额超过 5,000 元且不超过 50,000 元须由部门主管审批。"),
            HumanMessage(content="那帮我提交一个吧"),
        ]
    }
    r5 = await router_node(s_shift_app)
    assert r5["intent"] == "approval"

    # 4.6 Verify 6-turn history window cap (max 12 messages) & deduplication
    long_msgs = []
    for idx in range(10):
        long_msgs.append(HumanMessage(content=f"历史问题 {idx}"))
        long_msgs.append(AIMessage(content=f"历史回答 {idx}"))
    long_msgs.append(HumanMessage(content="当前问题"))
    extracted = _extract_recent_history(long_msgs, max_turns=6)
    assert len(extracted) == 12
    assert extracted[0] == ("user", "历史问题 4")
    assert extracted[-1] == ("assistant", "历史回答 9")


# ---------------------------------------------------------------------------
# 5. Tier 2 Lightweight Non-Thinking LLM Classifier & Fallback Guardrails
# ---------------------------------------------------------------------------


def test_parse_llm_router_json_robustness():
    """Verifies parser handles <think> blocks, code fences, and malformed outputs safely."""
    raw = '<think>user asks about stock</think>\n```json\n{"intent":"tool","secondary_intent":null,"tool_hint":"query_inventory","confidence":0.91,"reason":"check stock"}\n```'
    parsed = _parse_llm_router_json(raw)
    assert parsed is not None
    assert parsed["intent"] == "tool"
    assert parsed["tool_hint"] == "query_inventory"
    assert parsed["confidence"] == 0.91

    assert _parse_llm_router_json("not json at all") is None
    assert _parse_llm_router_json('{"intent": "invalid_enum"}') is None


@pytest.mark.asyncio
async def test_llm_contextual_classifier_and_safety_guard(monkeypatch):
    """Tests Tier 2 LLM routing, 6-turn prompt injection, safety guard override, and timeout fallback."""
    monkeypatch.setattr(settings, "ROUTER_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "ROUTER_LLM_TIMEOUT", 1.0)

    captured_prompts = []

    async def fake_llm_success(prompt_messages, timeout_sec):
        captured_prompts.append(prompt_messages)
        return '{"intent":"retrieve","secondary_intent":"tool","tool_hint":"query_inventory","confidence":0.92,"reason":"policy+stock"}'

    monkeypatch.setattr(router_module, "_invoke_router_llm", fake_llm_success)

    # Ambiguous query not intercepted by Tier 1 -> hits Tier 2 LLM with history
    res = await router_node(
        {
            "messages": [
                HumanMessage(content="我们部门下周要新来两位实习生"),
                AIMessage(content="好的，请问需要协助安排哪些事项？"),
                HumanMessage(content="看看他们配发电脑的安排"),
            ]
        }
    )
    assert res["intent"] == "retrieve"
    assert res["secondary_intent"] == "tool"
    assert res["metadata"]["routing_method"] == "llm_contextual"
    assert res["metadata"]["tool_hint"] == "query_inventory"
    assert len(captured_prompts) == 1
    assert "我们部门下周要新来两位实习生" in captured_prompts[0][1].content

    # Safety guard: LLM mistakenly predicts 'approval' on policy question -> overridden to 'retrieve'
    async def fake_llm_bad_approval(prompt_messages, timeout_sec):
        return '{"intent":"approval","secondary_intent":null,"tool_hint":null,"confidence":0.95,"reason":"mentions approve"}'

    monkeypatch.setattr(router_module, "_invoke_router_llm", fake_llm_bad_approval)
    guard_res = await router_node(
        {"messages": [HumanMessage(content="我想申请采购一台 8000 元的笔记本，需要谁审批？")]}
    )
    assert guard_res["intent"] == "retrieve"
    assert guard_res["metadata"]["routing_reason"] == "safety_guard_policy_over_approval"

    # Timeout fallback -> cleanly degrades to Tier 3 deterministic rules
    class _SlowDummyLLM:
        async def ainvoke(self, messages, config=None):
            await asyncio.sleep(2.0)
            return AIMessage(content='{"intent":"chat"}')

    # Restore original _invoke_router_llm so real asyncio.wait_for timeout is exercised
    monkeypatch.undo()
    monkeypatch.setattr(settings, "ROUTER_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "ROUTER_LLM_TIMEOUT", 0.05)
    monkeypatch.setattr(router_module, "get_router_llm", lambda timeout_sec=2.5: _SlowDummyLLM())

    fallback_res = await router_node(
        {
            "messages": [
                HumanMessage(content="一线城市出差住宿标准是多少"),
                AIMessage(content="[RAG Answer]: 一线城市住宿上限 600 元/晚。"),
                HumanMessage(content="二线城市呢？"),
            ]
        }
    )
    assert fallback_res["intent"] == "retrieve"
    assert fallback_res["metadata"]["routing_method"] == "fallback_contextual_rules"


@pytest.mark.asyncio
async def test_router_llm_stream_isolation_in_astream_events(monkeypatch):
    """Ensures Tier 2 router LLM classification never leaks JSON tokens into astream_events."""
    monkeypatch.setattr(settings, "ROUTER_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "ROUTER_LLM_TIMEOUT", 1.0)

    class _FastJsonRouterLLM:
        async def ainvoke(self, messages, config=None):
            # Verify callback isolation config was passed
            assert config is not None
            assert config.get("callbacks") == []
            return AIMessage(
                content='{"intent":"chat","secondary_intent":null,"tool_hint":null,"confidence":0.95,"reason":"casual"}'
            )

    monkeypatch.setattr(router_module, "get_router_llm", lambda timeout_sec=2.5: _FastJsonRouterLLM())

    streamed_chunks = []
    async for event in graph.astream_events(
        {
            "messages": [HumanMessage(content="周末准备去爬山放松一下")],
            "user_id": "u_iso",
            "session_id": "s_iso",
            "current_step": "init",
            "intent": "",
            "secondary_intent": "",
            "context": [],
            "metadata": {},
        },
        config={"configurable": {"thread_id": "thread_router_iso_0060"}},
        version="v2",
    ):
        if event.get("event") == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            text = getattr(chunk, "content", "") if chunk else ""
            if text:
                streamed_chunks.append(text)

    combined = "".join(streamed_chunks)
    assert '"intent":"chat"' not in combined
    assert "secondary_intent" not in combined


# ---------------------------------------------------------------------------
# 6. Compound Intent End-to-End StateGraph Trajectories (workflow.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compound_retrieve_then_tool_trajectory(disable_live_router_llm):
    """Validates acyclic compound graph execution: router -> retrieve -> tool -> generate -> END."""
    initial_state: AgentState = {
        "messages": [HumanMessage(content="先查一下IT运维部备用机借用标准，再帮我查一下MacBook库存")],
        "user_id": "u_compound_tool",
        "session_id": "s_compound_tool",
        "current_step": "init",
        "intent": "",
        "secondary_intent": "",
        "context": [],
        "metadata": {},
    }
    result = await graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "thread_compound_retrieve_tool_0060"}},
    )

    assert result["intent"] == "retrieve"
    assert result["secondary_intent"] == "tool"
    assert len(result.get("context", [])) > 0
    assert result["metadata"].get("tool_executed") is True
    assert any(isinstance(m, ToolMessage) and m.name == "query_inventory" for m in result["messages"])
    final_content = result["messages"][-1].content
    assert "[Tool Answer]" in final_content


@pytest.mark.asyncio
async def test_compound_retrieve_then_approval_trajectory(disable_live_router_llm, isolated_sqlite_db):
    """Validates compound retrieve -> approval triggers policy retrieval first, then approval interrupt."""
    thread_id = "thread_compound_retrieve_approval_0060"
    initial_state: AgentState = {
        "messages": [HumanMessage(content="请帮我核对研发部 MacBook Pro 采购申请的最新制度标准，并提交审批。")],
        "user_id": "u_compound_app",
        "session_id": "s_compound_app",
        "current_step": "init",
        "intent": "",
        "secondary_intent": "",
        "context": [],
        "metadata": {
            "thread_id": thread_id,
            "purchase_args": {
                "item_name": "MacBook Pro 16",
                "quantity": 1,
                "unit_price": 22999.0,
                "department": "研发部",
                "reason": "研发高配置采购",
            },
        },
    }
    config = {"configurable": {"thread_id": thread_id}}
    try:
        await graph.ainvoke(initial_state, config=config)
    except Exception:
        pass

    snapshot = graph.get_state(config)
    assert snapshot is not None
    assert snapshot.next == ("approval",)
    assert snapshot.values.get("intent") == "retrieve"
    assert snapshot.values.get("secondary_intent") == "approval"
    assert len(snapshot.values.get("context", [])) > 0

    pending = isolated_sqlite_db.query(Approval).filter(Approval.thread_id == thread_id).first()
    assert pending is not None
    assert pending.status == "PENDING"
    assert pending.total_price == 22999.0
