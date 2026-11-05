"""Hybrid Retrieval (BM25 + Qdrant Dense Vector) & Reranker Engine with RBAC Security."""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from backend.core.config import settings
from backend.rag.loader import load_sample_kb_documents
from backend.rag.splitter import split_documents
from backend.rag.vector_store import (
    get_qdrant_client,
    search_similar_documents,
    upsert_documents,
)


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
            meta = doc.metadata or {}
            raw_src = meta.get("source") or meta.get("filename") or ""
            norm_name = Path(raw_src).name if raw_src else "doc"
            chunk_idx = meta.get("chunk_index", 0)
            content_clean = doc.page_content.strip()
            content_hash = hashlib.md5(content_clean.encode("utf-8")).hexdigest()
            # Normalize doc_id so identical chunks from relative/absolute paths merge seamlessly
            doc_id = f"{norm_name}__chunk_{chunk_idx}__{content_hash}"
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
    """Semantic Reranker to score and refine top candidate documents with dynamic truncation."""

    def rerank(
        self,
        query: str,
        docs: List[Document],
        top_k: int = 5,
        min_score: Optional[float] = None,
        relative_threshold: Optional[float] = None,
        primary_domain: Optional[str] = None,
    ) -> List[Document]:
        """Calculates cross-semantic relevance scores for query and candidates,

        returning top_k refined documents with optional low-relevance noise truncation.
        """
        if not docs:
            return []

        query_tokens = set(tokenize_text(query))

        scored_docs: List[Document] = []
        for doc in docs:
            doc_tokens = set(tokenize_text(doc.page_content))

            # Compute token overlap & query coverage
            overlap = len(query_tokens.intersection(doc_tokens))
            query_coverage = overlap / (len(query_tokens) or 1.0)
            jaccard_sim = overlap / (len(query_tokens.union(doc_tokens)) or 1.0)
            semantic_overlap = 0.75 * query_coverage + 0.25 * jaccard_sim

            rrf_score = doc.metadata.get("rrf_score", 0.0)
            dense_score = doc.metadata.get("score", 0.0)

            # Combined hybrid rerank score
            combined_score = 0.5 * semantic_overlap + 0.3 * rrf_score + 0.2 * dense_score

            meta = doc.metadata.copy()
            meta["rerank_score"] = round(float(combined_score), 4)
            scored_docs.append(Document(page_content=doc.page_content, metadata=meta))

        scored_docs.sort(key=lambda x: x.metadata["rerank_score"], reverse=True)

        if not scored_docs:
            return []

        # If no cutoff parameters provided, return top_k candidates directly
        if min_score is None and relative_threshold is None and primary_domain is None:
            return scored_docs[:top_k]

        # Floor and relative dropoff filtering
        top_score = scored_docs[0].metadata["rerank_score"]
        top_cat = scored_docs[0].metadata.get("category", "")
        target_domain = primary_domain or top_cat

        filtered_docs: List[Document] = [scored_docs[0]]
        for d in scored_docs[1:]:
            s = d.metadata["rerank_score"]
            cat = d.metadata.get("category", "")

            # 1. Floor cutoff
            if min_score is not None and s < min_score:
                continue

            # 2. Relative dropoff cutoff (drop if score is < 60% of top hit)
            if relative_threshold is not None and s < top_score * relative_threshold:
                continue

            # 3. Cross-domain noise cutoff: if top hit is IT, and doc is FINANCE with much lower score, drop
            if target_domain and cat and cat.upper() != target_domain.upper() and s < 0.25:
                continue

            filtered_docs.append(d)
            if len(filtered_docs) >= top_k:
                break

        return filtered_docs


class HybridRetriever:
    """Main Hybrid Retriever orchestrator combining:

    1. Sparse BM25 Keyword Search (with RBAC)
    2. Dense Qdrant Vector Search (with RBAC Payload Filter)
    3. RRF Fusion
    4. Category Filtering
    5. Reranker Refinement
    """

    def __init__(self, sample_kb_dir: Optional[Path] = None, sync_to_qdrant: bool = True):
        kb_path = sample_kb_dir or Path("docs/sample_kb")
        raw_docs = load_sample_kb_documents(kb_path)
        self.sample_docs = split_documents(raw_docs, chunk_size=500, chunk_overlap=50) if raw_docs else []
        self.bm25_retriever = BM25Retriever(self.sample_docs)

        # Ensure sample docs are indexed in Qdrant as well, but skip re-indexing if points already exist
        if sync_to_qdrant and self.sample_docs:
            try:
                client = get_qdrant_client()
                col_info = client.get_collection(collection_name=settings.QDRANT_COLLECTION)
                points_count = getattr(col_info, "points_count", 0) or 0
                if points_count == 0:
                    upsert_documents(self.sample_docs, client=client)
            except Exception:
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
        sub_queries: Optional[List[str]] = None,
        primary_domain: Optional[str] = None,
    ) -> List[Document]:
        """Performs hybrid retrieval pipeline with RBAC Security:

        Dense Search + BM25 Search (across all sub-queries) -> RRF Fusion -> Category Filter -> Reranker -> Top-K Docs.
        """
        all_dense_results: List[List[Document]] = []
        all_bm25_results: List[List[Document]] = []

        target_queries = list(sub_queries) if sub_queries else [query]
        if query not in target_queries:
            target_queries.insert(0, query)

        for q in target_queries:
            # 1. Dense Vector Search from Qdrant with RBAC Filter
            dense = search_similar_documents(
                query=q,
                top_k=candidate_k,
                tenant_id=tenant_id,
                user_department=user_department,
                clearance_level=clearance_level,
            )
            all_dense_results.append(dense)

            # 2. BM25 Keyword Search with RBAC Filter
            bm25 = self.bm25_retriever.search(
                query=q,
                top_k=candidate_k,
                tenant_id=tenant_id,
                user_department=user_department,
                clearance_level=clearance_level,
            )
            all_bm25_results.append(bm25)

        # 3. RRF Fusion across all candidate lists
        combined_lists = all_dense_results + all_bm25_results
        fused_results = reciprocal_rank_fusion(combined_lists, k=60)

        # 4. Category Filter (if specified)
        effective_cat = category_filter or primary_domain
        if effective_cat:
            cat_matched = [
                doc for doc in fused_results
                if doc.metadata.get("category", "").upper() == effective_cat.upper()
            ]
            if cat_matched:
                fused_results = cat_matched

        # 5. Reranker 精排与强阈值截断
        reranker = Reranker()
        final_results = reranker.rerank(
            query=query,
            docs=fused_results,
            top_k=top_k,
            min_score=0.16,
            relative_threshold=0.60,
            primary_domain=effective_cat,
        )

        return final_results


_global_hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever(
    sample_kb_dir: Optional[Path] = None,
    force_refresh: bool = False,
) -> HybridRetriever:
    """Returns singleton HybridRetriever to prevent redundant disk I/O, BM25 indexing, and embedding computation."""
    global _global_hybrid_retriever
    if _global_hybrid_retriever is None or force_refresh:
        _global_hybrid_retriever = HybridRetriever(sample_kb_dir=sample_kb_dir)
    return _global_hybrid_retriever
