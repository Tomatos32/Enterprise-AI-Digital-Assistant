"""Comprehensive Unit & Integration Tests for Issue-0062 Hybrid Semantic Slot Extraction Engine.

Covers:
  1. Shared Chinese/Arabic numeric, quantity, unit-price, and total-price parsing.
  2. All 6 business tools + approval semantic slot extraction without fake defaults.
  3. Policy Strategy 5.1 Option A: automatic HR email resolution (unique, not found, ambiguous).
  4. Policy Strategy 5.2 Option A: strict prohibition on auto-filling ERP catalog prices
     (both deterministic and LLM anti-hallucination guard).
  5. Zero DB writes & zero interrupt() when required slots are missing.
  6. Multi-turn missing-slot completion loop (in-memory metadata & WebSocket pure-message reload)
     with dynamic 5,000 RMB threshold re-routing (<= 5,000 tool vs > 5,000 approval) and
     acyclic tool -> approval escalation guard.
  7. Lightweight non-thinking LLM timeout fallback, safe merge, and chat_ws stream isolation.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.adapters.mock_impl as mock_impl_module
import backend.api.v1.chat_ws as chat_ws_module
import backend.db.session as db_session_module
from backend.core.config import settings
from backend.db.session import Base
from backend.graph.nodes.approval_node import approval_node
from backend.graph.nodes.generate_node import generate_node
from backend.graph.nodes.router_node import router_node
from backend.graph.nodes.tool_node import tool_node
from backend.graph.state import AgentState
from backend.graph.workflow import build_graph, route_after_tool
from backend.models.approval import Approval
from backend.models.purchase import Purchase
from backend.models.ticket import Ticket
from backend.tools import slot_extractor
from backend.tools.slot_extractor import (
    detect_pending_clarification_context,
    extract_purchase_quantity_and_prices,
    extract_slots_for_tool,
    merge_purchase_amounts_across_turns,
    parse_chinese_number,
    parse_purchase_amount,
)

# Isolated in-memory SQLite database for zero side-effect verification
_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


@pytest.fixture(autouse=True)
def isolated_db_and_offline_llm(monkeypatch):
    """Creates clean SQLite tables and disables live network LLM calls by default."""
    Base.metadata.create_all(bind=_TEST_ENGINE)
    monkeypatch.setattr(db_session_module, "SessionLocal", _TestingSessionLocal)
    monkeypatch.setattr(mock_impl_module, "SessionLocal", _TestingSessionLocal)
    # Deterministic offline test mode (individual LLM tests override this explicitly)
    monkeypatch.setattr(settings, "SLOT_EXTRACTOR_LLM_ENABLED", False)
    monkeypatch.setattr(settings, "ROUTER_LLM_ENABLED", False)
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=_TEST_ENGINE)


# ---------------------------------------------------------------------------
# 1. Shared Numeric & Purchase Quantity/Price Parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("三千五", 3500.0),
        ("一万八", 18000.0),
        ("两万五千", 25000.0),
        ("2.5万", 25000.0),
        ("8k", 8000.0),
        ("12,500", 12500.0),
        ("十五", 15.0),
        ("两", 2.0),
    ],
)
def test_parse_chinese_number(token: str, expected: float):
    assert parse_chinese_number(token) == pytest.approx(expected)


def test_extract_purchase_quantity_and_prices_unit_and_total():
    # Quantity + explicit unit price
    r1 = extract_purchase_quantity_and_prices("申请采购 2 台 Dell 显示器，单价 3499 元")
    assert r1["quantity"] == 2
    assert r1["unit_price"] == pytest.approx(3499.0)
    assert r1["total_price"] == pytest.approx(6998.0)

    # Quantity + explicit total price -> derives unit price
    r2 = extract_purchase_quantity_and_prices("买3把人体工学椅共 12000 元")
    assert r2["quantity"] == 3
    assert r2["unit_price"] == pytest.approx(4000.0)
    assert r2["total_price"] == pytest.approx(12000.0)

    # Chinese numeral magnitude
    assert parse_purchase_amount("采购 MacBook Pro 16 一台，预算一万八") == pytest.approx(18000.0)


def test_merge_purchase_amounts_across_turns():
    merged_small = merge_purchase_amounts_across_turns(
        ["帮我采购 2 台显示器", "单价 2000 元"]
    )
    assert merged_small["quantity"] == 2
    assert merged_small["unit_price"] == pytest.approx(2000.0)
    assert merged_small["total_price"] == pytest.approx(4000.0)

    merged_large = merge_purchase_amounts_across_turns(
        ["帮我采购 2 台显示器", "单价 3500 元"]
    )
    assert merged_large["quantity"] == 2
    assert merged_large["unit_price"] == pytest.approx(3500.0)
    assert merged_large["total_price"] == pytest.approx(7000.0)

    merged_total_first = merge_purchase_amounts_across_turns(
        ["预算共 12000 元采购办公椅", "买 3 把"]
    )
    assert merged_total_first["quantity"] == 3
    assert merged_total_first["total_price"] == pytest.approx(12000.0)
    assert merged_total_first["unit_price"] == pytest.approx(4000.0)


# ---------------------------------------------------------------------------
# 2. All 6 Tools Semantic Slot Extraction (Zero Hardcoded Defaults)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_employee_slots_complete_and_missing():
    ok = await extract_slots_for_tool(
        "query_employee",
        "帮我查一下研发部李娜的联系方式",
        [HumanMessage(content="帮我查一下研发部李娜的联系方式")],
    )
    assert ok.is_complete
    assert ok.slots["name"] == "李娜"
    assert ok.slots.get("department") == "研发部"

    emp_id_res = await extract_slots_for_tool(
        "query_employee",
        "查询工号 EMP-1001",
        [HumanMessage(content="查询工号 EMP-1001")],
    )
    assert emp_id_res.is_complete
    assert emp_id_res.slots["name"] == "EMP-1001"

    missing = await extract_slots_for_tool(
        "query_employee",
        "帮我查一下员工信息",
        [HumanMessage(content="帮我查一下员工信息")],
    )
    assert not missing.is_complete
    assert "name" in missing.missing_slots
    assert missing.slots.get("name") is None
    assert "姓名" in missing.clarification_question


@pytest.mark.asyncio
async def test_query_inventory_slots_complete_and_missing():
    ok = await extract_slots_for_tool(
        "query_inventory",
        "帮我查一下 ThinkPad X1 Carbon 库存还有几台",
        [HumanMessage(content="帮我查一下 ThinkPad X1 Carbon 库存还有几台")],
    )
    assert ok.is_complete
    assert ok.slots["item_name"] == "ThinkPad X1 Carbon"

    missing = await extract_slots_for_tool(
        "query_inventory",
        "帮我查一下库存",
        [HumanMessage(content="帮我查一下库存")],
    )
    assert not missing.is_complete
    assert "item_name" in missing.missing_slots
    assert "MacBook" not in str(missing.slots)


@pytest.mark.asyncio
async def test_create_ticket_slots_complete_and_missing():
    ok = await extract_slots_for_tool(
        "create_ticket",
        "公司 VPN 无法登录，紧急报修",
        [HumanMessage(content="公司 VPN 无法登录，紧急报修")],
    )
    assert ok.is_complete
    assert "VPN" in ok.slots["title"]
    assert ok.slots["priority"] == "P1"
    assert ok.slots["department"] == "IT"

    missing = await extract_slots_for_tool(
        "create_ticket",
        "帮我建个工单",
        [HumanMessage(content="帮我建个工单")],
    )
    assert not missing.is_complete
    assert "title" in missing.missing_slots
    assert missing.slots.get("title") != "客服支持工单"


@pytest.mark.asyncio
async def test_search_knowledge_base_slots():
    ok = await extract_slots_for_tool(
        "search_knowledge_base",
        "帮我检索差旅住宿报销标准",
        [HumanMessage(content="帮我检索差旅住宿报销标准")],
    )
    assert ok.is_complete
    assert "报销" in ok.slots["query"] or "差旅" in ok.slots["query"]


# ---------------------------------------------------------------------------
# 3. Strategy 5.1 Option A: send_email Automatic HR Email Resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_email_option_a_unique_hr_match():
    q = "请给张伟发邮件，主题是系统巡检通知，内容：今晚八点执行例行巡检。"
    res = await extract_slots_for_tool("send_email", q, [HumanMessage(content=q)])
    assert res.is_complete
    assert res.resolved_from_hr is True
    assert res.slots["to_email"] == "zhangwei@company.com"
    assert "巡检" in res.slots["subject"]
    assert "例行巡检" in res.slots["body"]


@pytest.mark.asyncio
async def test_send_email_option_a_hr_not_found_asks_clarification():
    q = "请给陈子涵发邮件，主题是项目同步，内容：请下午三点参会。"
    res = await extract_slots_for_tool("send_email", q, [HumanMessage(content=q)])
    assert not res.is_complete
    assert "to_email" in res.missing_slots
    assert res.resolved_from_hr is False
    assert "陈子涵" in res.clarification_question
    assert "admin@company.com" not in str(res.slots)


@pytest.mark.asyncio
async def test_send_email_option_a_hr_ambiguous_candidates_asks_disambiguation():
    class _AmbiguousHRAdapter:
        def get_employee(self, id_or_name: str, department: str | None = None) -> Dict[str, Any]:
            return {
                "status": "SUCCESS",
                "count": 2,
                "data": [
                    {"name": "张伟", "department": "研发部", "email": "zhangwei.rd@enterprise.com"},
                    {"name": "张伟", "department": "财务部", "email": "zhangwei.fin@enterprise.com"},
                ],
            }

    q = "给张伟发邮件，内容：请确认季度预算表。"
    with patch.object(slot_extractor, "get_hr_adapter", return_value=_AmbiguousHRAdapter()):
        res = await extract_slots_for_tool("send_email", q, [HumanMessage(content=q)])

    assert not res.is_complete
    assert "to_email" in res.missing_slots
    assert len(res.hr_candidates) == 2
    assert "研发部" in res.clarification_question
    assert "财务部" in res.clarification_question


# ---------------------------------------------------------------------------
# 4. Strategy 5.2 Option A: Strict Prohibition on Fabricating Catalog Prices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_option_a_never_autofills_catalog_price():
    q = "帮我采购 2 台 MacBook Pro 16"
    res = await extract_slots_for_tool("create_purchase", q, [HumanMessage(content=q)])
    assert not res.is_complete
    assert "unit_price" in res.missing_slots
    assert res.slots.get("item_name") == "MacBook Pro 16"
    assert res.slots.get("quantity") == 2
    assert "unit_price" not in res.slots
    assert "22999" not in res.clarification_question
    assert "不自动套用目录参考价" in res.clarification_question


@pytest.mark.asyncio
async def test_purchase_option_a_blocks_llm_hallucinated_price(monkeypatch):
    monkeypatch.setattr(settings, "SLOT_EXTRACTOR_LLM_ENABLED", True)
    hallucinated_json = '{"item_name": "MacBook Pro 16", "quantity": 2, "unit_price": 22999.0}'
    q = "帮我申请采购两台 MacBook Pro 16"
    with patch.object(
        slot_extractor,
        "_invoke_slot_extractor_llm",
        new=AsyncMock(return_value=hallucinated_json),
    ):
        res = await extract_slots_for_tool("approval", q, [HumanMessage(content=q)])

    assert not res.is_complete
    assert "unit_price" in res.missing_slots
    assert "unit_price" not in res.slots


# ---------------------------------------------------------------------------
# 5. Zero DB Writes & Zero interrupt() When Required Slots Are Missing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_node_missing_slots_causes_zero_db_writes(isolated_db_and_offline_llm):
    db = isolated_db_and_offline_llm
    state: AgentState = {
        "messages": [HumanMessage(content="帮我建个工单")],
        "metadata": {"tool_hint": "create_ticket"},
    }
    out = await tool_node(state)
    assert out["current_step"] == "slot_clarification_needed"
    assert out["metadata"]["tool_executed"] is False
    assert out["metadata"]["slot_clarification_needed"] is True
    assert out["metadata"]["pending_slot_tool"] == "create_ticket"
    assert db.query(Ticket).count() == 0

    # generate_node passes clarification deterministically without emoji or internal jargon
    gen_out = await generate_node(
        {
            "messages": state["messages"],
            "intent": "tool",
            "metadata": out["metadata"],
            "context": [],
        }
    )
    reply = str(gen_out["messages"][-1].content)
    assert "工单" in reply
    assert "主题" in reply or "描述" in reply


@pytest.mark.asyncio
async def test_approval_node_missing_price_zero_db_writes_and_zero_interrupt(isolated_db_and_offline_llm):
    db = isolated_db_and_offline_llm
    local_graph = build_graph()
    config = {"configurable": {"thread_id": "thread_missing_price_no_interrupt"}}
    initial_state: AgentState = {
        "messages": [HumanMessage(content="帮我提交 MacBook Pro 16 的采购审批")],
        "intent": "approval",
        "metadata": {"thread_id": "thread_missing_price_no_interrupt"},
    }
    final_state = await local_graph.ainvoke(initial_state, config=config)

    # Graph finishes cleanly to END without pausing on interrupt()
    snapshot = local_graph.get_state(config)
    assert snapshot.next == ()
    assert db.query(Approval).count() == 0
    assert db.query(Purchase).count() == 0
    assert final_state["metadata"]["slot_clarification_needed"] is True
    assert "预估单价或总预算" in str(final_state["messages"][-1].content)


# ---------------------------------------------------------------------------
# 6. Multi-Turn Missing-Slot Completion Loop & Dynamic Threshold Re-Routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_turn_purchase_clarification_small_executes_tool(isolated_db_and_offline_llm):
    db = isolated_db_and_offline_llm
    # Turn 1: User asks to purchase 2 monitors without price
    turn1_q = "帮我申请采购 2 台 Dell UltraSharp 显示器"
    r1 = await router_node({"messages": [HumanMessage(content=turn1_q)], "metadata": {}})
    assert r1["intent"] == "tool"
    assert r1["metadata"]["tool_hint"] == "create_purchase"

    t1 = await tool_node({"messages": [HumanMessage(content=turn1_q)], "metadata": r1["metadata"]})
    assert t1["current_step"] == "slot_clarification_needed"
    clarification_q = t1["metadata"]["slot_clarification_question"]
    assert db.query(Purchase).count() == 0
    assert db.query(Approval).count() == 0

    # Turn 2: Simulate WebSocket DB reload (pure messages history, NO pending metadata carried)
    turn2_messages = [
        HumanMessage(content=turn1_q),
        AIMessage(content=clarification_q),
        HumanMessage(content="单价 2000 元"),
    ]
    ctx = detect_pending_clarification_context(turn2_messages, {}, current_query="单价 2000 元")
    assert ctx is not None
    assert ctx["pending_tool"] == "create_purchase"

    r2 = await router_node({"messages": turn2_messages, "metadata": {}})
    assert r2["intent"] == "tool"
    assert r2["metadata"]["tool_hint"] == "create_purchase"
    assert r2["metadata"]["routing_method"] == "slot_clarification_resume"
    assert r2["metadata"]["parsed_purchase_amount"] == pytest.approx(4000.0)

    t2 = await tool_node({"messages": turn2_messages, "metadata": r2["metadata"]})
    assert t2["current_step"] == "tool_executed"
    assert t2["metadata"]["tool_executed"] is True
    assert t2["metadata"]["extracted_tool_args"]["item_name"] == "Dell UltraSharp 显示器"
    assert t2["metadata"]["extracted_tool_args"]["quantity"] == 2
    assert t2["metadata"]["extracted_tool_args"]["unit_price"] == pytest.approx(2000.0)
    assert db.query(Purchase).count() == 1
    assert db.query(Approval).count() == 0


@pytest.mark.asyncio
async def test_multi_turn_purchase_clarification_over_5000_reroutes_to_approval_interrupt(
    isolated_db_and_offline_llm,
):
    db = isolated_db_and_offline_llm
    local_graph = build_graph()
    config = {"configurable": {"thread_id": "thread_multiturn_approval_001"}}

    # Turn 1: Missing price -> returns polite clarification
    turn1_q = "帮我申请采购 2 台 Dell UltraSharp 显示器"
    res1 = await local_graph.ainvoke(
        {
            "messages": [HumanMessage(content=turn1_q)],
            "metadata": {"thread_id": "thread_multiturn_approval_001", "display_name": "林悦"},
        },
        config=config,
    )
    clarification_q = str(res1["messages"][-1].content)
    assert "预估单价或总预算" in clarification_q
    assert db.query(Approval).count() == 0

    # Turn 2: Pure messages history reload with unit price 3500 -> total 7000 > 5000 -> interrupt()
    config2 = {"configurable": {"thread_id": "thread_multiturn_approval_002"}}
    turn2_messages = [
        HumanMessage(content=turn1_q),
        AIMessage(content=clarification_q),
        HumanMessage(content="单价 3500 元，研发部日常开发使用"),
    ]
    await local_graph.ainvoke(
        {
            "messages": turn2_messages,
            "metadata": {"thread_id": "thread_multiturn_approval_002", "display_name": "林悦"},
        },
        config=config2,
    )
    snap = local_graph.get_state(config2)
    assert snap.next == ("approval",)
    pending_app = db.query(Approval).filter(Approval.thread_id == "thread_multiturn_approval_002").first()
    assert pending_app is not None
    assert pending_app.status == "PENDING"
    assert pending_app.item_name == "Dell UltraSharp 显示器"
    assert pending_app.quantity == 2
    assert pending_app.unit_price == pytest.approx(3500.0)
    assert pending_app.total_price == pytest.approx(7000.0)

    # Verify interrupt payload carries full authentic fields (quantity, unit_price, applicant, total_price)
    interrupt_payload = snap.tasks[0].interrupts[0].value
    assert interrupt_payload["quantity"] == 2
    assert interrupt_payload["unit_price"] == pytest.approx(3500.0)
    assert interrupt_payload["total_price"] == pytest.approx(7000.0)
    assert interrupt_payload["applicant"] == "林悦"
    assert interrupt_payload["item_name"] == "Dell UltraSharp 显示器"


@pytest.mark.asyncio
async def test_tool_node_escalates_over_5000_purchase_to_approval():
    state: AgentState = {
        "messages": [HumanMessage(content="采购 2 台显示器，单价 3600 元")],
        "metadata": {"tool_hint": "create_purchase"},
    }
    out = await tool_node(state)
    assert out["current_step"] == "escalated_to_approval"
    assert out["metadata"]["tool_executed"] is False
    assert out["metadata"]["escalate_to_approval"] is True
    assert out["metadata"]["purchase_args"]["quantity"] == 2
    assert out["metadata"]["purchase_args"]["unit_price"] == pytest.approx(3600.0)
    assert route_after_tool({"metadata": out["metadata"]}) == "approval"


@pytest.mark.asyncio
async def test_multi_turn_send_email_completion_with_hr_resolution():
    turn1_q = "帮我给张伟发一封邮件"
    t1 = await tool_node(
        {"messages": [HumanMessage(content=turn1_q)], "metadata": {"tool_hint": "send_email"}}
    )
    assert t1["current_step"] == "slot_clarification_needed"
    assert "body" in t1["metadata"]["missing_slots"]
    clarification_q = t1["metadata"]["slot_clarification_question"]
    assert "zhangwei@company.com" in clarification_q

    turn2_messages = [
        HumanMessage(content=turn1_q),
        AIMessage(content=clarification_q),
        HumanMessage(content="主题是巡检提醒，内容是请核对本周机房巡检报告"),
    ]
    r2 = await router_node({"messages": turn2_messages, "metadata": {}})
    assert r2["intent"] == "tool"
    assert r2["metadata"]["tool_hint"] == "send_email"

    t2 = await tool_node({"messages": turn2_messages, "metadata": r2["metadata"]})
    assert t2["current_step"] == "tool_executed"
    assert t2["metadata"]["extracted_tool_args"]["to_email"] == "zhangwei@company.com"
    assert "巡检" in t2["metadata"]["extracted_tool_args"]["body"]


# ---------------------------------------------------------------------------
# 7. LLM Fallback Resilience, Backward Compatibility & WS Stream Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_fallback_timeout_degrades_gracefully_and_valid_json_merges(monkeypatch):
    monkeypatch.setattr(settings, "SLOT_EXTRACTOR_LLM_ENABLED", True)

    # 7A. Timeout / None -> deterministic result preserved cleanly
    with patch.object(slot_extractor, "_invoke_slot_extractor_llm", new=AsyncMock(return_value=None)):
        res_timeout = await extract_slots_for_tool(
            "query_inventory",
            "帮我看看仓库还有什么",
            [HumanMessage(content="帮我看看仓库还有什么")],
        )
        assert not res_timeout.is_complete
        assert res_timeout.extraction_method == "deterministic"

    # 7B. Valid LLM JSON with explicit price cue in user text -> safely merges
    q = "研发组这边新项目立项需要一台定制工作站，报价单写了 9800 块"
    llm_payload = '{"item_name": "定制工作站", "quantity": 1, "unit_price": 9800, "department": "研发部"}'
    with patch.object(slot_extractor, "_invoke_slot_extractor_llm", new=AsyncMock(return_value=llm_payload)):
        res_llm = await extract_slots_for_tool("approval", q, [HumanMessage(content=q)])
        assert res_llm.is_complete
        assert res_llm.extraction_method == "hybrid_llm"
        assert res_llm.slots["item_name"] == "定制工作站"
        assert res_llm.slots["unit_price"] == pytest.approx(9800.0)


@pytest.mark.asyncio
async def test_approval_node_explicit_purchase_args_under_threshold_auto_approves(
    isolated_db_and_offline_llm,
):
    db = isolated_db_and_offline_llm
    out = await approval_node(
        {
            "messages": [HumanMessage(content="提交小额采购")],
            "metadata": {
                "thread_id": "thread_small_explicit",
                "purchase_args": {
                    "item_name": "Logitech MX Master 3S",
                    "quantity": 2,
                    "unit_price": 699.0,
                    "department": "研发部",
                    "reason": "新员工入职配发",
                },
            },
        }
    )
    assert out["current_step"] == "approval_completed"
    assert out["metadata"]["approval_executed"] is True
    assert out["metadata"]["extracted_purchase_args"]["total_price"] == pytest.approx(1398.0)
    assert db.query(Purchase).count() == 1
    assert db.query(Approval).count() == 0


@pytest.mark.asyncio
async def test_tool_node_explicit_ai_tool_calls_preserved():
    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "id": "call_explicit_inv_1",
                "name": "query_inventory",
                "args": {"item_name": "MacBook Pro 16"},
            }
        ],
    )
    out = await tool_node({"messages": [ai_msg], "metadata": {}})
    assert out["current_step"] == "tool_executed"
    assert out["metadata"]["tool_executed"] is True
    assert "MacBook Pro 16" in out["metadata"]["tool_output"]


def test_chat_ws_stream_isolation_guards_internal_slot_extractor():
    ws_source = inspect.getsource(chat_ws_module.process_ws_chat_stream)
    assert '"internal_slot_extractor"' in ws_source
    assert '("router", "retrieve", "tool", "approval")' in ws_source
