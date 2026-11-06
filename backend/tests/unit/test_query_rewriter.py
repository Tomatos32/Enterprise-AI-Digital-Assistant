"""Unit Tests for Enterprise Query Rewriter, Sub-Query Decomposition, and Rerank Truncation."""

from langchain_core.messages import AIMessage, HumanMessage
from backend.rag.query_rewriter import get_query_rewriter
from backend.rag.retriever import get_hybrid_retriever


def test_query_rewriter_sub_query_decomposition():
    """Tests sub-query decomposition for multi-facet composite question."""
    rewriter = get_query_rewriter()
    q = "我出差需要临时借用备用机，期限是多久，需要交押金吗，超借用期限怎么办，要扣钱吗"
    res = rewriter.rewrite(q)

    assert res.primary_domain == "IT"
    assert len(res.sub_queries) >= 3
    # Check that facets are accurately identified
    combined_subs = " ".join(res.sub_queries)
    assert "借用期限" in combined_subs
    assert "押金" in combined_subs
    assert "超期" in combined_subs
    # Situational "出差" should not contaminate the core IT sub-queries
    assert not any("出差报销" in sq for sq in res.sub_queries)


def test_query_rewriter_coreference_resolution():
    """Tests pronoun replacement using multi-turn conversational history."""
    rewriter = get_query_rewriter()
    history = [
        HumanMessage(content="研发部配置的 MacBook Pro 16 性能如何？"),
        AIMessage(content="MacBook Pro 16 配备 M3 Max 芯片与 36G 内存，支持高性能编译。"),
    ]
    query_with_pronoun = "那台电脑可以申请外借吗？"
    res = rewriter.rewrite(query_with_pronoun, history=history)

    assert "MacBook" in res.standalone_query or "电脑" in res.standalone_query


def test_retrieval_truncation_filters_out_irrelevant_finance_doc():
    """Tests that Reranker dynamic cutoff eliminates cross-domain noise (e.g. 04_FINANCE)."""
    retriever = get_hybrid_retriever()
    rewriter = get_query_rewriter()

    composite_q = "我出差需要临时借用备用机，期限是多久，需要交押金吗，超借用期限怎么办，要扣钱吗"
    rw = rewriter.rewrite(composite_q)

    docs = retriever.retrieve(
        query=rw.standalone_query,
        top_k=3,
        sub_queries=rw.sub_queries,
        primary_domain=rw.primary_domain,
    )

    assert len(docs) > 0
    # Must contain 03_IT
    assert any("03_IT" in d.metadata.get("filename", "") for d in docs)
    # Must NOT contain 04_FINANCE because it is cross-domain noise
    assert not any("04_FINANCE" in d.metadata.get("filename", "") for d in docs)
