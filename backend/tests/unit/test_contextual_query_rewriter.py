"""Comprehensive Unit & Integration Tests for Issue-0061:
Multi-Turn Coreference Resolution, Implicit Ellipsis Completion,
Hybrid Contextual Query Rewriting, Cross-Domain Soft-Weighted Retrieval,
Graph RAG Standalone Query Alignment, and Startup BM25 Upload Sync.
"""

import asyncio
from pathlib import Path
from typing import Any, List
from unittest.mock import patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

import backend.core.knowledge_ledger as ledger_module
from backend.graph.nodes.retrieve_node import retrieve_node
from backend.graph.state import AgentState
from backend.graph.workflow import graph
from backend.rag.query_rewriter import (
    QueryRewriter,
    _parse_llm_rewriter_json,
)
from backend.rag.retriever import HybridRetriever, Reranker, get_hybrid_retriever


class _FakeAsyncClient:
    """Tracks whether async HTTP client is cleanly closed after LLM invocation."""

    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class _FakeRewriterLLM:
    """Mock lightweight non-thinking LLM for deterministic rewriter testing."""

    def __init__(self, response_text: str, delay: float = 0.0, should_fail: bool = False) -> None:
        self._response_text = response_text
        self._delay = delay
        self._should_fail = should_fail
        self.http_async_client = _FakeAsyncClient()
        self.calls: List[Any] = []

    async def ainvoke(self, messages: List[BaseMessage], config: Any = None, **kwargs: Any) -> AIMessage:
        self.calls.append({"messages": messages, "config": config})
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._should_fail:
            raise RuntimeError("Simulated upstream rewriter failure")
        return AIMessage(content=self._response_text)


def test_pronoun_and_implicit_ellipsis_resolution() -> None:
    """Verifies explicit pronoun coreference AND pronoun-free implicit ellipsis completion."""
    rewriter = QueryRewriter()

    # 1. Explicit pronoun resolution
    history_mac = [
        HumanMessage(content="研发部配置的 MacBook Pro 16 性能如何？"),
        AIMessage(content="MacBook Pro 16 配备 M3 Max 芯片与 36G 内存。"),
    ]
    res_mac = rewriter.rewrite("那台电脑可以申请外借吗？", history=history_mac)
    assert res_mac.coreference_resolved is True
    assert "MacBook Pro 16" in res_mac.standalone_query
    assert "IT" in res_mac.domains

    # 2. Implicit ellipsis without pronoun: trip city -> lodging standard
    history_trip = [
        HumanMessage(content="我要去北京出差一周"),
        AIMessage(content="好的，请问您需要查询北京出差的哪项报销标准？"),
    ]
    res_trip = rewriter.rewrite("住宿标准是多少？", history=history_trip)
    assert res_trip.coreference_resolved is True
    assert "北京" in res_trip.standalone_query
    assert "出差" in res_trip.standalone_query
    assert "住宿标准" in res_trip.standalone_query
    assert "FINANCE" in res_trip.domains

    # 3. Implicit ellipsis without pronoun: overdue penalty follow-up
    history_borrow = [
        HumanMessage(content="临时借用备用机最长能借多久？"),
        AIMessage(content="单次借用期限最长为 14 天。"),
    ]
    res_overdue = rewriter.rewrite("超了会怎样？", history=history_borrow)
    assert res_overdue.coreference_resolved is True
    assert "备用机" in res_overdue.standalone_query
    assert "IT" in res_overdue.domains
    assert any("超期" in sq for sq in res_overdue.sub_queries)

    # 4. Implicit ellipsis without pronoun: required proof documents
    history_sick = [
        HumanMessage(content="员工带薪病假每年有几天？"),
        AIMessage(content="每年提供 5 天全额带薪病假。"),
    ]
    res_proof = rewriter.rewrite("需要什么凭证？", history=history_sick)
    assert res_proof.coreference_resolved is True
    assert "病假" in res_proof.standalone_query
    assert "HR" in res_proof.domains


def test_parallel_sibling_followups_without_pronouns() -> None:
    """Verifies parallel sibling contrast follow-ups substitute sibling terms cleanly without merging."""
    rewriter = QueryRewriter()

    # 1. Leave type sibling substitution: 年假 -> 产假
    res_maternity = rewriter.rewrite(
        "那产假呢？",
        history=[
            HumanMessage(content="公司年假有几天？"),
            AIMessage(content="根据工龄提供 5 到 15 天带薪年假。"),
        ],
    )
    assert res_maternity.coreference_resolved is True
    assert "产假" in res_maternity.standalone_query
    assert "年假" not in res_maternity.standalone_query
    assert "几天" in res_maternity.standalone_query
    assert "HR" in res_maternity.domains

    # 2. City tier sibling substitution: 一线城市 -> 二线城市
    res_tier2 = rewriter.rewrite(
        "二线城市呢？",
        history=[
            HumanMessage(content="一线城市出差住宿标准是多少？"),
            AIMessage(content="普通员工一类城市住宿上限为 550 元/晚。"),
        ],
    )
    assert res_tier2.coreference_resolved is True
    assert "二线城市" in res_tier2.standalone_query
    assert "一线城市" not in res_tier2.standalone_query
    assert "住宿标准" in res_tier2.standalone_query
    assert "FINANCE" in res_tier2.domains

    # 3. Rank sibling substitution: 普通员工 -> 部门经理
    res_mgr = rewriter.rewrite(
        "那部门经理呢？",
        history=[
            HumanMessage(content="普通员工出差一线城市住宿标准是多少？"),
            AIMessage(content="普通员工为 550 元/晚。"),
        ],
    )
    assert res_mgr.coreference_resolved is True
    assert "部门经理" in res_mgr.standalone_query
    assert "一线城市" in res_mgr.standalone_query
    assert "普通员工" not in res_mgr.standalone_query
    assert "住宿标准" in res_mgr.standalone_query

    # 4. Severity sibling substitution: P1 -> P0
    res_p0 = rewriter.rewrite(
        "P0呢？",
        history=[
            HumanMessage(content="P1 故障的响应 SLA 是多久？"),
            AIMessage(content="P1 紧急故障响应 SLA 为 15 分钟内。"),
        ],
    )
    assert res_p0.coreference_resolved is True
    assert "P0" in res_p0.standalone_query
    assert "SLA" in res_p0.standalone_query

    # 5. 3-turn chained parallel sibling follow-up (年假 -> 那产假呢？ -> 陪产假呢？) & attribute follow-up
    chain_history = [
        HumanMessage(content="公司年假有几天？"),
        AIMessage(content="员工每年享有 5 到 15 天年假。"),
        HumanMessage(content="那产假呢？"),
        AIMessage(content="女员工享受 158 天产假。"),
    ]
    res_paternity = rewriter.rewrite("陪产假呢？", history=chain_history)
    assert res_paternity.coreference_resolved is True
    assert "陪产假" in res_paternity.standalone_query
    assert "几天" in res_paternity.standalone_query
    assert "年假" not in res_paternity.standalone_query

    res_maternity_attr = rewriter.rewrite("怎么申请？", history=chain_history)
    assert res_maternity_attr.coreference_resolved is True
    assert "产假" in res_maternity_attr.standalone_query


def test_topic_switch_isolation_and_custom_uploaded_doc_followup() -> None:
    """Ensures unrelated topic switches are never polluted while custom uploaded doc topics carry over."""
    rewriter = QueryRewriter()

    # 1. Explicit topic switch (HR -> FINANCE): must NOT carry over 年假
    res_switch = rewriter.rewrite(
        "公司发票抬头和纳税人识别号是什么？",
        history=[
            HumanMessage(content="公司年假有几天？"),
            AIMessage(content="员工每年享有 5 到 15 天年假。"),
        ],
    )
    assert res_switch.coreference_resolved is False
    assert "年假" not in res_switch.standalone_query
    assert res_switch.domains == ["FINANCE"]

    # 2. Dynamic entity extraction & carry-over for newly uploaded custom document topic
    history_custom = [
        HumanMessage(content="研发GPU集群配额制度里 A100算力节点 有什么规定？"),
        AIMessage(content="默认单项目配额为 8 卡 A100 算力节点。"),
    ]
    res_custom = rewriter.rewrite("超过配额怎么审批？", history=history_custom)
    assert res_custom.coreference_resolved is True
    assert any(tok in res_custom.standalone_query for tok in ("A100", "GPU集群"))


def test_multi_domain_scoring_without_hard_single_domain_lock() -> None:
    """Verifies hard IT override is removed and cross-domain queries emit multi-domain soft weights."""
    rewriter = QueryRewriter()

    # 1. Cross-domain IT + FINANCE composite query
    res_cross = rewriter.rewrite("出差借备用机并按一线城市标准报销")
    assert "IT" in res_cross.domains
    assert "FINANCE" in res_cross.domains
    assert res_cross.domain_weights["IT"] > 0
    assert res_cross.domain_weights["FINANCE"] > 0

    # 2. Procurement of laptops must rank PROCUREMENT #1 (no longer hijacked by hard IT override)
    res_proc = rewriter.rewrite("采购10台MacBook笔记本电脑需要什么审批流程和三方比价要求")
    assert res_proc.primary_domain == "PROCUREMENT"
    assert "PROCUREMENT" in res_proc.domains
    assert "IT" in res_proc.domains

    # 3. Tri-domain query (HR + IT + SECURITY)
    res_tri = rewriter.rewrite("员工离职时电脑怎么归还，需要签保密协议和做数据擦除吗")
    assert {"HR", "IT", "SECURITY"}.issubset(set(res_tri.domains))

    # 4. Pure IT situational trip mention must NOT be contaminated with FINANCE
    res_pure_it = rewriter.rewrite("我出差需要临时借用备用机，期限是多久，需要交押金吗，超借用期限怎么办，要扣钱吗")
    assert res_pure_it.domains == ["IT"]
    assert res_pure_it.primary_domain == "IT"
    assert not any("出差报销" in sq for sq in res_pure_it.sub_queries)


def test_universal_six_domain_decomposition() -> None:
    """Verifies domain detection and adaptive sub-query expansion across all 6 enterprise domains."""
    rewriter = QueryRewriter()
    cases = [
        ("试用期转正和绩效PIP 90天改进考核有什么规定？", "HR", "PIP"),
        ("新供应商准入资质审核和三方对账划款流程是什么？", "PROCUREMENT", "供应商"),
        ("VPN 远程访问最大时长和开源协议 GPL 禁令是什么？", "IT", "VPN"),
        ("公司发票抬头、纳税人识别号以及商务招待宴请标准是多少？", "FINANCE", "纳税人识别号"),
        ("绝密数据加密要求和外部公有云大模型使用禁令是什么？", "SECURITY", "绝密"),
        ("客服工单 Critical 升级矩阵和 L2 主管客户退款赔偿限额是多少？", "CS", "赔偿"),
    ]
    for query, expected_domain, expected_term in cases:
        res = rewriter.rewrite(query)
        assert expected_domain in res.domains, f"Expected {expected_domain} for query '{query}', got {res.domains}"
        assert len(res.sub_queries) >= 1
        combined = " ".join(res.sub_queries)
        assert expected_term in combined, f"Expected '{expected_term}' in sub-queries {res.sub_queries}"


def test_cross_domain_soft_weighted_retrieval_preserves_both_domains() -> None:
    """Verifies soft domain weighting recalls BOTH domains for cross-domain queries and protects GENERAL docs."""
    rewriter = QueryRewriter()
    retriever = get_hybrid_retriever()

    # 1. Cross-domain query: IT borrowing + FINANCE travel standard
    q_cross = "出差借备用机并按一线城市标准报销"
    rw_cross = rewriter.rewrite(q_cross)
    docs_cross = retriever.retrieve(
        query=rw_cross.standalone_query,
        top_k=4,
        sub_queries=rw_cross.sub_queries,
        primary_domain=rw_cross.primary_domain,
        domains=rw_cross.domains,
        domain_weights=rw_cross.domain_weights,
    )
    cats_cross = {str(d.metadata.get("category", "")).upper() for d in docs_cross}
    assert "IT" in cats_cross, f"Expected IT doc in cross-domain retrieval, got {cats_cross}"
    assert "FINANCE" in cats_cross, f"Expected FINANCE doc in cross-domain retrieval, got {cats_cross}"

    # 2. Procurement + Laptop query must retrieve 02_PROCUREMENT (previously dropped by IT hard lock)
    q_proc = "采购10台MacBook笔记本电脑需要什么审批流程和三方比价要求"
    rw_proc = rewriter.rewrite(q_proc)
    docs_proc = retriever.retrieve(
        query=rw_proc.standalone_query,
        top_k=4,
        sub_queries=rw_proc.sub_queries,
        primary_domain=rw_proc.primary_domain,
        domains=rw_proc.domains,
        domain_weights=rw_proc.domain_weights,
    )
    assert any(
        "PROCUREMENT" == str(d.metadata.get("category", "")).upper() for d in docs_proc
    ), f"Expected PROCUREMENT doc, got {[d.metadata.get('filename') for d in docs_proc]}"

    # 3. Explicit hard category_filter contract remains strict when explicitly specified
    docs_hard = retriever.retrieve(
        query="出差住宿和备用机",
        top_k=3,
        category_filter="FINANCE",
    )
    assert len(docs_hard) >= 1
    assert all(str(d.metadata.get("category", "")).upper() == "FINANCE" for d in docs_hard)

    # 4. Reranker never hard-drops GENERAL/custom uploaded docs under single-domain weighting
    reranker = Reranker()
    candidate_docs = [
        Document(
            page_content="临时设备备用机借用期限最长14天，超期扣减200元。",
            metadata={"filename": "03_IT.md", "category": "IT", "rrf_score": 0.03, "score": 0.85},
        ),
        Document(
            page_content="研发部门特殊备用机出差借用补充规定：需提前登记项目编号。",
            metadata={"filename": "custom_notice.md", "category": "GENERAL", "rrf_score": 0.028, "score": 0.82},
        ),
    ]
    ranked = reranker.rerank(
        query="研发部门备用机借用规定",
        docs=candidate_docs,
        top_k=2,
        min_score=0.10,
        relative_threshold=0.50,
        primary_domain="IT",
        domains=["IT"],
        domain_weights={"IT": 1.0},
    )
    assert len(ranked) == 2
    assert any(d.metadata.get("filename") == "custom_notice.md" for d in ranked)


@pytest.mark.asyncio
async def test_llm_rewriter_json_parsing_safety_guard_and_timeout_fallback() -> None:
    """Verifies LLM JSON parsing (<think>/fences), safety guards, client cleanup, and timeout fallback."""
    # 1. Robust JSON parser handles <think> blocks and markdown code fences
    raw_with_think = (
        "<think>分析对话历史后发现用户问的是产假天数</think>\n"
        "```json\n"
        '{"standalone_query": "公司产假和陪产假分别是多少天？", '
        '"sub_queries": ["产假 158天", "陪产假 15天"], '
        '"domains": ["HR", "INVALID_DOM"], "entities": ["产假", "陪产假"], "coreference_resolved": true}\n'
        "```"
    )
    parsed = _parse_llm_rewriter_json(raw_with_think)
    assert parsed is not None
    assert parsed["standalone_query"] == "公司产假和陪产假分别是多少天？"
    assert parsed["domains"] == ["HR"]
    assert parsed["coreference_resolved"] is True

    rewriter = QueryRewriter()

    # 2. Live LLM path succeeds, applies safety guard against FINANCE contamination & false coref on single-turn, and closes async client
    contaminated_json = (
        '{"standalone_query": "我出差需要临时借用备用机，借用期限是多久？", '
        '"sub_queries": ["备用机 借用期限", "出差报销 标准"], '
        '"domains": ["IT", "FINANCE"], "entities": ["备用机"], "coreference_resolved": true}'
    )
    fake_llm = _FakeRewriterLLM(contaminated_json)
    with patch("backend.rag.query_rewriter.get_rewriter_llm", return_value=fake_llm):
        res_llm = await rewriter.arewrite("我出差需要临时借用备用机，借用期限是多久？")
    assert res_llm.rewrite_method == "llm"
    assert res_llm.coreference_resolved is False
    assert "IT" in res_llm.domains
    assert "FINANCE" not in res_llm.domains
    assert not any("出差报销" in sq for sq in res_llm.sub_queries)
    assert fake_llm.http_async_client.closed is True
    assert fake_llm.calls[0]["config"] == {"callbacks": [], "tags": ["internal_rewriter"]}

    # 3. Unresolved-pronoun guard: LLM fails to resolve '它' -> falls back to deterministic rewrite
    lazy_llm = _FakeRewriterLLM(
        '{"standalone_query": "它的参考单价是多少？", "sub_queries": ["它的参考单价"], '
        '"domains": ["IT"], "entities": [], "coreference_resolved": false}'
    )
    with patch("backend.rag.query_rewriter.get_rewriter_llm", return_value=lazy_llm):
        res_guard = await rewriter.arewrite(
            "它的参考单价是多少？",
            history=[HumanMessage(content="研发部标准开发机 MacBook Pro M3 怎么样？")],
        )
    assert res_guard.rewrite_method == "deterministic"
    assert "MacBook Pro M3" in res_guard.standalone_query
    assert lazy_llm.http_async_client.closed is True

    # 4. Timeout gracefully falls back to deterministic engine without raising
    slow_llm = _FakeRewriterLLM('{"standalone_query": "timeout"}', delay=0.4)
    with (
        patch("backend.rag.query_rewriter.get_rewriter_llm", return_value=slow_llm),
        patch("backend.rag.query_rewriter.settings.QUERY_REWRITER_LLM_TIMEOUT", 0.05),
    ):
        res_timeout = await rewriter.arewrite(
            "那产假呢？",
            history=[HumanMessage(content="公司年假有几天？")],
        )
    assert res_timeout.rewrite_method == "deterministic"
    assert "产假" in res_timeout.standalone_query
    assert slow_llm.http_async_client.closed is True


@pytest.mark.asyncio
async def test_rewriter_llm_stream_isolation_in_astream_events() -> None:
    """Ensures internal query rewriter LLM tokens inside retrieve_node never leak through WS event guard."""
    rewriter_json = (
        '{"standalone_query": "带薪年休假天数规定是多少？", '
        '"sub_queries": ["带薪年休假 计提矩阵"], '
        '"domains": ["HR"], "entities": ["年假"], "coreference_resolved": false}'
    )
    fake_llm = _FakeRewriterLLM(rewriter_json)

    initial_state: AgentState = {
        "messages": [HumanMessage(content="请问公司员工带薪年休假每年有多少天规定？")],
        "user_id": "u_rewriter_iso",
        "session_id": "s_rewriter_iso",
        "current_step": "init",
        "metadata": {},
    }
    config = {"configurable": {"thread_id": "thread_rewriter_iso_0061"}}

    user_visible_tokens: List[str] = []
    with (
        patch("backend.rag.query_rewriter.get_rewriter_llm", return_value=fake_llm),
        patch("backend.graph.nodes.router_node.get_router_llm", return_value=None),
    ):
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            if event.get("event") == "on_chat_model_stream":
                event_meta = event.get("metadata") or {}
                event_tags = event.get("tags") or []
                if (
                    event_meta.get("langgraph_node") in ("router", "retrieve")
                    or "internal_router" in event_tags
                    or "internal_rewriter" in event_tags
                ):
                    continue
                if event.get("name") in ["ChatOpenAI", "EnterpriseChatOpenAI", "NativeOllamaChatModel"]:
                    continue
                chunk = event.get("data", {}).get("chunk")
                if chunk and getattr(chunk, "content", ""):
                    user_visible_tokens.append(chunk.content)

    rendered = "".join(user_visible_tokens)
    assert rendered.strip() != ""
    assert '"standalone_query"' not in rendered
    assert '"sub_queries"' not in rendered


@pytest.mark.asyncio
async def test_retrieve_node_passes_standalone_query_to_graph_rag() -> None:
    """Verifies retrieve_node feeds rewritten standalone_query into Graph RAG for multi-turn reasoning."""
    # 1. Pronoun follow-up targeting Knowledge Graph entity MacBook Pro M3
    state_pronoun: AgentState = {
        "messages": [
            HumanMessage(content="研发部的标准开发机 MacBook Pro M3 怎么样？"),
            AIMessage(content="研发部标准开发机为 MacBook Pro M3。"),
            HumanMessage(content="它的参考单价是多少？"),
        ],
        "user_id": "u_graph_coref",
        "session_id": "s_graph_coref",
        "current_step": "init",
        "context": [],
        "metadata": {"existing_flag": "keep_me"},
    }
    with patch("backend.rag.query_rewriter.get_rewriter_llm", return_value=None):
        res_pronoun = await retrieve_node(state_pronoun)

    assert res_pronoun["current_step"] == "retrieved"
    assert res_pronoun["metadata"]["existing_flag"] == "keep_me"
    assert res_pronoun["metadata"]["coreference_resolved"] is True
    assert "MacBook Pro M3" in res_pronoun["metadata"]["rewritten_query"]

    graph_ctx = next(
        (c for c in res_pronoun["context"] if c.get("metadata", {}).get("type") == "graph_rag_topological_reasoning"),
        None,
    )
    assert graph_ctx is not None
    assert "MacBook Pro M3" in graph_ctx["metadata"]["detected_entities"]
    assert "¥16,000" in graph_ctx["content"]

    # 2. Parallel sibling follow-up targeting Knowledge Graph department 市场部
    state_sibling: AgentState = {
        "messages": [
            HumanMessage(content="研发部主管采购审批上限是多少？"),
            AIMessage(content="研发部主管为技术总监，采购单笔审批上限为 ¥20,000。"),
            HumanMessage(content="那市场部呢？"),
        ],
        "user_id": "u_graph_sibling",
        "session_id": "s_graph_sibling",
        "current_step": "init",
        "context": [],
        "metadata": {},
    }
    with patch("backend.rag.query_rewriter.get_rewriter_llm", return_value=None):
        res_sibling = await retrieve_node(state_sibling)

    graph_ctx_2 = next(
        (c for c in res_sibling["context"] if c.get("metadata", {}).get("type") == "graph_rag_topological_reasoning"),
        None,
    )
    assert graph_ctx_2 is not None
    assert "市场部" in graph_ctx_2["metadata"]["detected_entities"]
    assert "¥15,000" in graph_ctx_2["content"]


def test_hybrid_retriever_startup_loads_uploaded_backend_data_into_bm25(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulates server restart: HybridRetriever loads top-level uploaded docs into BM25, skips subdirs & corrupt files."""
    sample_dir = tmp_path / "sample_kb"
    sample_dir.mkdir(parents=True)
    (sample_dir / "01_HR_base.md").write_text("# HR 基线制度\n\n标准年假为 5 天。", encoding="utf-8")

    data_dir = tmp_path / "backend_data"
    data_dir.mkdir(parents=True)
    (data_dir / "quantum_cluster_policy.md").write_text(
        "# 量子算力集群配额制度\n\n单部门量子算力集群配额上限为 16 卡，超限须提交首席科学家特批。",
        encoding="utf-8",
    )
    (data_dir / "remote_lab_notice.txt").write_text(
        "远程实验室门禁补充通知：实验区刷卡记录保留 180 天。",
        encoding="utf-8",
    )
    # Corrupt PDF must be skipped gracefully without crashing startup
    (data_dir / "corrupt_upload.pdf").write_bytes(b"not-a-valid-pdf")
    # Subdirectory (like qdrant_storage/) must NOT be traversed
    qdrant_subdir = data_dir / "qdrant_storage"
    qdrant_subdir.mkdir(parents=True)
    (qdrant_subdir / "ignored_nested.md").write_text("SHOULD_NEVER_BE_INDEXED_FROM_SUBDIR", encoding="utf-8")

    # Isolated knowledge ledger with explicit category override for uploaded file
    temp_ledger = tmp_path / "logs" / "knowledge_tasks_ledger.json"
    monkeypatch.setattr(ledger_module, "LEDGER_PATH", temp_ledger)
    ledger_module.reset_ledger_cache()
    ledger_module.record_uploaded_document(
        filename="quantum_cluster_policy.md",
        category="IT",
        file_format="md",
        size_bytes=120,
        chunks_indexed=1,
        last_task_id="sync-restart-test",
        execution_mode="sync",
        uploader="admin",
    )

    try:
        restarted_retriever = HybridRetriever(
            sample_kb_dir=sample_dir,
            uploaded_data_dir=data_dir,
            sync_to_qdrant=False,
        )

        # BM25 immediately finds uploaded doc after cold startup with ledger category override
        hits = restarted_retriever.bm25_retriever.search("量子算力集群 16卡 首席科学家特批", top_k=3)
        assert len(hits) >= 1
        assert hits[0].metadata["filename"] == "quantum_cluster_policy.md"
        assert hits[0].metadata["category"] == "IT"
        assert hits[0].metadata["source_type"] == "uploaded"

        # TXT uploaded doc is also loaded
        txt_hits = restarted_retriever.bm25_retriever.search("远程实验室 门禁 180天", top_k=3)
        assert any(h.metadata["filename"] == "remote_lab_notice.txt" for h in txt_hits)

        # Subdirectory markdown inside qdrant_storage/ must NOT be indexed
        subdir_hits = restarted_retriever.bm25_retriever.search("SHOULD_NEVER_BE_INDEXED_FROM_SUBDIR", top_k=3)
        assert len(subdir_hits) == 0
    finally:
        ledger_module.reset_ledger_cache()
