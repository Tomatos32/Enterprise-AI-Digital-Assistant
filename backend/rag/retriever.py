"""Hybrid Retrieval (BM25 + Qdrant Dense Vector) & Soft-Weighted Cross-Domain Reranker Engine with RBAC Security."""

import hashlib
import inspect
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from backend.core.config import settings
from backend.rag.loader import load_sample_kb_documents, load_uploaded_data_documents
from backend.rag.splitter import split_documents
from backend.rag.vector_store import (
    get_qdrant_client,
    search_similar_documents,
    upsert_documents,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SAMPLE_KB_DIR = _PROJECT_ROOT / "docs" / "sample_kb"
DEFAULT_UPLOADED_DATA_DIR = _PROJECT_ROOT / "backend" / "data"


def tokenize_text(text: str) -> List[str]:
    """Tokenizes Chinese characters, English words, and numbers for BM25 indexing.

    E.g., "采购60000元" -> ["采", "购", "60000", "元"]
    """
    if not text:
        return []
    tokens = re.findall(r"[一-龥]|[a-zA-Z]+|\d+", text.lower())
    return tokens if tokens else [text.lower()]


def _compute_token_overlap(query_tokens: Set[str], doc_tokens: Set[str]) -> float:
    """Computes blended query coverage (75%) + Jaccard similarity (25%) between token sets."""
    if not query_tokens or not doc_tokens:
        return 0.0
    overlap = len(query_tokens.intersection(doc_tokens))
    query_coverage = overlap / len(query_tokens)
    jaccard_sim = overlap / len(query_tokens.union(doc_tokens))
    return 0.75 * query_coverage + 0.25 * jaccard_sim


def _get_uploaded_category_overrides() -> Dict[str, str]:
    """Safely fetches admin-assigned category overrides from the persistent knowledge ledger."""
    try:
        from backend.core.knowledge_ledger import get_uploaded_documents_map

        doc_map = get_uploaded_documents_map()
        overrides: Dict[str, str] = {}
        for filename, entry in doc_map.items():
            cat = entry.get("category")
            if isinstance(cat, str) and cat.strip():
                overrides[filename] = cat.strip().upper()
        return overrides
    except Exception as exc:
        logger.debug("Unable to read uploaded document category overrides: %s", exc)
        return {}


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
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
            else:
                # Preserve highest dense similarity score across sub-queries if present
                existing_dense = float(doc_map[doc_id].metadata.get("score", 0.0) or 0.0)
                new_dense = float(meta.get("score", 0.0) or 0.0)
                if new_dense > existing_dense:
                    merged_meta = doc_map[doc_id].metadata.copy()
                    merged_meta["score"] = new_dense
                    doc_map[doc_id] = Document(page_content=doc_map[doc_id].page_content, metadata=merged_meta)

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
    """Semantic Reranker with soft multi-domain weighting, sub-query awareness, and dynamic noise truncation."""

    def _resolve_domain_weights(
        self,
        primary_domain: Optional[str],
        domains: Optional[Sequence[str]],
        domain_weights: Optional[Dict[str, float]],
    ) -> Dict[str, float]:
        """Normalizes inferred target domains into a soft weight map in [0.0, 1.0]."""
        if domain_weights:
            cleaned = {
                str(k).strip().upper(): max(0.0, min(1.0, float(v)))
                for k, v in domain_weights.items()
                if str(k).strip()
            }
            if cleaned:
                return cleaned
        if domains:
            weights: Dict[str, float] = {}
            for idx, dom in enumerate(domains):
                d_up = str(dom).strip().upper()
                if d_up and d_up not in weights:
                    weights[d_up] = round(max(0.50, 1.0 - idx * 0.12), 4)
            if weights:
                return weights
        if primary_domain and str(primary_domain).strip():
            return {str(primary_domain).strip().upper(): 1.0}
        return {}

    def rerank(
        self,
        query: str,
        docs: List[Document],
        top_k: int = 5,
        min_score: Optional[float] = None,
        relative_threshold: Optional[float] = None,
        primary_domain: Optional[str] = None,
        domains: Optional[List[str]] = None,
        domain_weights: Optional[Dict[str, float]] = None,
        sub_queries: Optional[List[str]] = None,
    ) -> List[Document]:
        """Calculates cross-semantic relevance scores with soft multi-domain weights and diversity preservation."""
        if not docs:
            return []

        query_tokens = set(tokenize_text(query))
        sub_token_sets: List[Set[str]] = []
        if sub_queries and len(sub_queries) > 1:
            for sq in sub_queries:
                toks = set(tokenize_text(sq))
                if toks:
                    sub_token_sets.append(toks)

        effective_weights = self._resolve_domain_weights(primary_domain, domains, domain_weights)
        is_multi_domain = len(effective_weights) >= 2

        scored_docs: List[Document] = []
        for doc in docs:
            doc_tokens = set(tokenize_text(doc.page_content))
            full_overlap = _compute_token_overlap(query_tokens, doc_tokens)

            # Sub-query aware semantic overlap prevents cross-domain token dilution
            if sub_token_sets:
                best_sub_overlap = max(_compute_token_overlap(sq_toks, doc_tokens) for sq_toks in sub_token_sets)
                semantic_overlap = max(full_overlap, 0.90 * best_sub_overlap)
            else:
                semantic_overlap = full_overlap

            rrf_score = float(doc.metadata.get("rrf_score", 0.0) or 0.0)
            dense_score = float(doc.metadata.get("score", 0.0) or 0.0)

            base_score = 0.5 * semantic_overlap + 0.3 * rrf_score + 0.2 * dense_score

            # Soft domain weighting (never hard-drops GENERAL or uploaded custom docs)
            doc_cat = str(doc.metadata.get("category", "") or "").upper()
            domain_factor = 1.0
            applied_weight = 1.0
            if effective_weights:
                if doc_cat in effective_weights:
                    applied_weight = effective_weights[doc_cat]
                    domain_factor = 1.0 + 0.18 * applied_weight
                elif doc_cat in ("", "GENERAL"):
                    applied_weight = 1.0
                    domain_factor = 1.0
                else:
                    applied_weight = 0.0
                    domain_factor = 0.80 if is_multi_domain else 0.72

            combined_score = base_score * domain_factor

            meta = doc.metadata.copy()
            meta["rerank_score"] = round(float(combined_score), 4)
            meta["domain_weight"] = round(float(applied_weight), 4)
            scored_docs.append(Document(page_content=doc.page_content, metadata=meta))

        scored_docs.sort(key=lambda x: x.metadata["rerank_score"], reverse=True)

        if not scored_docs:
            return []

        # If no cutoff parameters provided, return top_k candidates directly
        if min_score is None and relative_threshold is None and not effective_weights:
            return scored_docs[:top_k]

        top_score = scored_docs[0].metadata["rerank_score"]
        top_cat = str(scored_docs[0].metadata.get("category", "") or "").upper()
        single_target_domain = (
            next(iter(effective_weights.keys()))
            if len(effective_weights) == 1
            else (top_cat if not effective_weights else "")
        )

        # Multi-domain diversity selection: ensure each matched domain with an eligible hit gets representation
        if is_multi_domain and top_k >= 2:
            selected: List[Document] = []
            selected_ids: Set[int] = set()
            relaxed_rel = min(relative_threshold, 0.42) if relative_threshold is not None else None

            # Pass 1: Reserve top eligible candidate per target domain
            for target_dom in effective_weights.keys():
                for idx, doc in enumerate(scored_docs):
                    if idx in selected_ids:
                        continue
                    cat = str(doc.metadata.get("category", "") or "").upper()
                    score = doc.metadata["rerank_score"]
                    if cat != target_dom:
                        continue
                    if min_score is not None and score < min_score:
                        continue
                    if relaxed_rel is not None and score < top_score * relaxed_rel:
                        continue
                    selected.append(doc)
                    selected_ids.add(idx)
                    break
                if len(selected) >= top_k:
                    break

            # Pass 2: Always guarantee the global #1 hit is included
            if 0 not in selected_ids:
                selected.insert(0, scored_docs[0])
                selected_ids.add(0)

            # Pass 3: Fill remaining slots by descending rerank score under quality gates
            for idx, doc in enumerate(scored_docs):
                if len(selected) >= top_k:
                    break
                if idx in selected_ids:
                    continue
                score = doc.metadata["rerank_score"]
                cat = str(doc.metadata.get("category", "") or "").upper()
                if min_score is not None and score < min_score:
                    continue
                is_target_cat = cat in effective_weights or cat in ("", "GENERAL")
                rel_gate = relaxed_rel if is_target_cat else relative_threshold
                if rel_gate is not None and score < top_score * rel_gate:
                    continue
                if not is_target_cat and score < 0.28:
                    continue
                selected.append(doc)
                selected_ids.add(idx)

            selected.sort(key=lambda x: x.metadata["rerank_score"], reverse=True)
            return selected[:top_k]

        # Single-domain or domain-agnostic dynamic truncation
        filtered_docs: List[Document] = [scored_docs[0]]
        for doc in scored_docs[1:]:
            if len(filtered_docs) >= top_k:
                break
            score = doc.metadata["rerank_score"]
            cat = str(doc.metadata.get("category", "") or "").upper()

            # 1. Floor cutoff
            if min_score is not None and score < min_score:
                continue

            # 2. Relative dropoff cutoff
            if relative_threshold is not None and score < top_score * relative_threshold:
                continue

            # 3. Single-domain cross-domain noise cutoff (never hard-drops GENERAL/uploaded docs)
            if (
                single_target_domain
                and cat
                and cat != "GENERAL"
                and cat != single_target_domain
                and score < max(0.28, top_score * 0.80)
            ):
                continue

            filtered_docs.append(doc)

        return filtered_docs


class HybridRetriever:
    """Main Hybrid Retriever orchestrator combining:

    1. Startup synchronization of built-in docs/sample_kb + admin-uploaded backend/data/ into BM25
    2. Sparse BM25 Keyword Search (with RBAC)
    3. Dense Qdrant Vector Search (with RBAC Payload Filter)
    4. RRF Fusion
    5. Explicit Category Filter (only when caller explicitly specifies category_filter)
    6. Soft-Weighted Cross-Domain Reranker Refinement
    """

    def __init__(
        self,
        sample_kb_dir: Optional[Path] = None,
        uploaded_data_dir: Optional[Path] = None,
        sync_to_qdrant: bool = True,
        include_uploaded_data: bool = True,
    ):
        kb_path = sample_kb_dir if sample_kb_dir is not None else DEFAULT_SAMPLE_KB_DIR
        builtin_raw_docs = load_sample_kb_documents(kb_path)

        uploaded_raw_docs: List[Document] = []
        if include_uploaded_data:
            data_path = uploaded_data_dir if uploaded_data_dir is not None else DEFAULT_UPLOADED_DATA_DIR
            category_overrides = _get_uploaded_category_overrides()
            uploaded_raw_docs = load_uploaded_data_documents(
                data_path,
                category_overrides=category_overrides,
            )

        raw_docs = builtin_raw_docs + uploaded_raw_docs
        self.sample_docs = split_documents(raw_docs, chunk_size=500, chunk_overlap=50) if raw_docs else []
        self.bm25_retriever = BM25Retriever(self.sample_docs)

        if uploaded_raw_docs:
            logger.info(
                "[HybridRetriever] Initialized BM25 with %d builtin + %d uploaded raw docs (%d chunks).",
                len(builtin_raw_docs),
                len(uploaded_raw_docs),
                len(self.sample_docs),
            )

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
        top_k: Optional[int] = None,
        category_filter: Optional[str] = None,
        candidate_k: int = 20,
        tenant_id: Optional[str] = "default",
        user_department: Optional[str] = None,
        clearance_level: Optional[int] = 1,
        sub_queries: Optional[List[str]] = None,
        primary_domain: Optional[str] = None,
        min_score: Optional[float] = None,
        domains: Optional[List[str]] = None,
        domain_weights: Optional[Dict[str, float]] = None,
    ) -> List[Document]:
        """Performs hybrid retrieval pipeline with RBAC Security and soft multi-domain ranking."""
        from backend.core.runtime_config import get_runtime_config

        runtime_cfg = get_runtime_config()
        effective_top_k = top_k if top_k is not None else runtime_cfg.rag_top_k
        effective_min_score = min_score if min_score is not None else runtime_cfg.rag_min_score

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

        # 4. Explicit Hard Category Filter ONLY when caller explicitly specifies category_filter
        if category_filter:
            cat_matched = [
                doc for doc in fused_results
                if doc.metadata.get("category", "").upper() == category_filter.upper()
            ]
            if cat_matched:
                fused_results = cat_matched

        # 5. Soft-Weighted Multi-Domain Reranker & Dynamic Truncation
        reranker = Reranker()
        rerank_kwargs: Dict[str, Any] = {
            "query": query,
            "docs": fused_results,
            "top_k": effective_top_k,
            "min_score": effective_min_score,
            "relative_threshold": 0.60,
            "primary_domain": category_filter or primary_domain,
        }
        try:
            sig_params = inspect.signature(reranker.rerank).parameters
            accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_params.values())
            if not category_filter and domains and (accepts_var_kw or "domains" in sig_params):
                rerank_kwargs["domains"] = domains
            if not category_filter and domain_weights and (accepts_var_kw or "domain_weights" in sig_params):
                rerank_kwargs["domain_weights"] = domain_weights
            if len(target_queries) > 1 and (accepts_var_kw or "sub_queries" in sig_params):
                rerank_kwargs["sub_queries"] = target_queries
        except (TypeError, ValueError):
            pass

        final_results = reranker.rerank(**rerank_kwargs)

        return final_results


_global_hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever(
    sample_kb_dir: Optional[Path] = None,
    uploaded_data_dir: Optional[Path] = None,
    force_refresh: bool = False,
) -> HybridRetriever:
    """Returns singleton HybridRetriever to prevent redundant disk I/O, BM25 indexing, and embedding computation."""
    global _global_hybrid_retriever
    if _global_hybrid_retriever is None or force_refresh:
        _global_hybrid_retriever = HybridRetriever(
            sample_kb_dir=sample_kb_dir,
            uploaded_data_dir=uploaded_data_dir,
        )
    return _global_hybrid_retriever
