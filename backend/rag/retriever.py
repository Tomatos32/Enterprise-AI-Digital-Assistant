"""Hybrid Retrieval (BM25 + Qdrant Dense Vector) & Reranker Engine with RBAC Security."""

import re
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from backend.rag.loader import load_sample_kb_documents
from backend.rag.vector_store import search_similar_documents, upsert_documents


def tokenize_text(text: str) -> List[str]:
    """Tokenizes Chinese characters, English words, and numbers for BM25 indexing.

    E.g., "采购60000元" -> ["采", "购", "60000", "元"]
    """
    if not text:
        return []
    tokens = re.findall(r"[一-龥]|[a-zA-Z]+|\d+", text.lower())
    return tokens if tokens else [text.lower()]


class BM25Retriever:
    """Sparse Keyword Retriever backed by rank_bm25 BM25Okapi with RBAC filter support."""

    def __init__(self, docs: Optional[List[Document]] = None):
        self.docs: List[Document] = docs or []
        self.bm25: Optional[BM25Okapi] = None
        if self.docs:
            self.build_index(self.docs)

    def build_index(self, docs: List[Document]):
        """Builds BM25 inverted index from documents."""
        self.docs = docs
        corpus = [tokenize_text(doc.page_content) for doc in docs]
        self.bm25 = BM25Okapi(corpus)

    def search(
        self,
        query: str,
        top_k: int = 20,
        tenant_id: Optional[str] = None,
        user_department: Optional[str] = None,
        clearance_level: Optional[int] = None,
    ) -> List[Document]:
        """Searches BM25 index and returns top_k matching documents with scores

        enforcing RBAC and multi-tenancy filters.
        """
        if not self.bm25 or not self.docs:
            return []

        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Zip documents with scores and sort descending
        doc_scores = list(zip(self.docs, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        results: List[Document] = []
        for doc, score in doc_scores:
            if score <= 0:
                continue

            meta = doc.metadata.copy()

            # RBAC in-memory filtering for BM25
            if tenant_id is not None:
                doc_tenant = meta.get("tenant_id", "default")
                if doc_tenant != tenant_id:
                    continue

            if user_department is not None:
                allowed_depts = meta.get("allowed_departments", ["ALL"])
                if "ALL" not in allowed_depts and user_department not in allowed_depts:
                    continue

            if clearance_level is not None:
                doc_clearance = meta.get("security_clearance_level", 1)
                if doc_clearance > clearance_level:
                    continue

            meta["bm25_score"] = float(score)
            results.append(Document(page_content=doc.page_content, metadata=meta))
            if len(results) >= top_k:
                break

        return results


def reciprocal_rank_fusion(
    results_list: List[List[Document]],
    k: int = 60,
) -> List[Document]:
    r"""Reciprocal Rank Fusion (RRF) algorithm to combine multiple ranked retrieval lists.

    RRF_Score(d) = \sum_{m \in M} 1 / (k + r_m(d))
    """
    rrf_scores: Dict[str, float] = {}
    doc_map: Dict[str, Document] = {}

    for results in results_list:
        for rank, doc in enumerate(results):
            # Use content hash + title as unique doc identifier
            doc_id = f"{doc.metadata.get('source', '')}_{hash(doc.page_content)}"
            doc_map[doc_id] = doc

            score = 1.0 / (k + (rank + 1))
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + score

    # Sort merged documents by RRF score descending
    sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    fused_docs: List[Document] = []
    for doc_id in sorted_doc_ids:
        doc = doc_map[doc_id]
        meta = doc.metadata.copy()
        meta["rrf_score"] = float(rrf_scores[doc_id])
        fused_docs.append(Document(page_content=doc.page_content, metadata=meta))

    return fused_docs


class Reranker:
    """Semantic Reranker to score and refine top candidate documents."""

    def rerank(self, query: str, docs: List[Document], top_k: int = 5) -> List[Document]:
        """Calculates cross-semantic relevance scores for query and candidates,

        returning top_k refined documents sorted by rerank_score.
        """
        if not docs:
            return []

        query_tokens = set(tokenize_text(query))

        scored_docs: List[Document] = []
        for doc in docs:
            doc_tokens = set(tokenize_text(doc.page_content))

            # Compute token overlap & RRF weight boost
            overlap = len(query_tokens.intersection(doc_tokens))
            jaccard_sim = overlap / (len(query_tokens.union(doc_tokens)) or 1.0)

            rrf_score = doc.metadata.get("rrf_score", 0.0)
            dense_score = doc.metadata.get("score", 0.0)

            # Combined hybrid rerank score
            combined_score = 0.5 * jaccard_sim + 0.3 * rrf_score + 0.2 * dense_score

            meta = doc.metadata.copy()
            meta["rerank_score"] = round(float(combined_score), 4)
            scored_docs.append(Document(page_content=doc.page_content, metadata=meta))

        scored_docs.sort(key=lambda x: x.metadata["rerank_score"], reverse=True)
        return scored_docs[:top_k]


class HybridRetriever:
    """Main Hybrid Retriever orchestrator combining:

    1. Sparse BM25 Keyword Search (with RBAC)
    2. Dense Qdrant Vector Search (with RBAC Payload Filter)
    3. RRF Fusion
    4. Category Filtering
    5. Reranker Refinement
    """

    def __init__(self, sample_kb_dir: Optional[Path] = None):
        kb_path = sample_kb_dir or Path("docs/sample_kb")
        self.sample_docs = load_sample_kb_documents(kb_path)
        self.bm25_retriever = BM25Retriever(self.sample_docs)

        # Ensure sample docs are indexed in Qdrant as well
        if self.sample_docs:
            upsert_documents(self.sample_docs)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None,
        candidate_k: int = 20,
        tenant_id: Optional[str] = "default",
        user_department: Optional[str] = None,
        clearance_level: Optional[int] = 1,
    ) -> List[Document]:
        """Performs hybrid retrieval pipeline with RBAC Security:

        Dense Search + BM25 Search -> RRF Fusion -> Category Filter -> Reranker -> Top-K Docs.
        """
        # 1. Dense Vector Search from Qdrant with RBAC Filter
        dense_results = search_similar_documents(
            query=query,
            top_k=candidate_k,
            tenant_id=tenant_id,
            user_department=user_department,
            clearance_level=clearance_level,
        )

        # 2. BM25 Keyword Search with RBAC Filter
        bm25_results = self.bm25_retriever.search(
            query=query,
            top_k=candidate_k,
            tenant_id=tenant_id,
            user_department=user_department,
            clearance_level=clearance_level,
        )

        # 3. RRF Fusion
        fused_results = reciprocal_rank_fusion([dense_results, bm25_results], k=60)

        # 4. Category Filter (if specified)
        if category_filter:
            fused_results = [
                doc for doc in fused_results
                if doc.metadata.get("category", "").upper() == category_filter.upper()
            ]

        # 5. Reranker 精排
        reranker = Reranker()
        final_results = reranker.rerank(query=query, docs=fused_results, top_k=top_k)

        return final_results
