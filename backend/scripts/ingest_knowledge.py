"""One-Click Offline Enterprise Knowledge Ingestion & Indexing Pipeline.

Recursively scans docs/sample_kb (Markdown, PDF, Excel), parses documents,
applies semantic text chunking, computes dense vector embeddings,
persists vectors into Qdrant vector database, and executes self-check diagnostic probes.

Usage:
    python -m backend.scripts.ingest_knowledge
    python backend/scripts/ingest_knowledge.py --recreate --chunk-size 500
"""

import argparse
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from qdrant_client import QdrantClient  # noqa: E402
from qdrant_client.http.models import Distance, VectorParams  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.rag.loader import load_sample_kb_documents  # noqa: E402
from backend.rag.splitter import split_documents  # noqa: E402
from backend.rag.vector_store import (  # noqa: E402
    get_embedding_engine_info,
    get_qdrant_client,
    get_qdrant_info,
    search_similar_documents,
    upsert_documents,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def ingest_knowledge_base(
    kb_dir: Optional[Path] = None,
    collection_name: Optional[str] = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    recreate: bool = False,
    verify: bool = True,
    client: Optional[QdrantClient] = None,
) -> Dict[str, Any]:
    """Orchestrates end-to-end knowledge document ingestion into Qdrant."""
    start_time = time.time()
    target_kb_dir = kb_dir or (Path(__file__).resolve().parent.parent.parent / "docs" / "sample_kb")
    col_name = collection_name or settings.QDRANT_COLLECTION

    logger.info("=" * 60)
    logger.info("Enterprise AI Knowledge Ingestion Pipeline")
    logger.info("Knowledge Directory: %s", target_kb_dir.resolve())
    logger.info("Target Qdrant Collection: %s", col_name)
    logger.info("Chunk Size: %d, Chunk Overlap: %d", chunk_size, chunk_overlap)
    logger.info("Recreate Collection: %s", recreate)
    logger.info("=" * 60)

    if not target_kb_dir.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {target_kb_dir}")

    # 1. Acquire Qdrant Client
    q_client = client or get_qdrant_client()

    # 2. Recreate collection if requested
    if recreate:
        try:
            collections = [c.name for c in q_client.get_collections().collections]
            if col_name in collections:
                q_client.delete_collection(collection_name=col_name)
                logger.info("Deleted existing collection '%s'", col_name)
            q_client.create_collection(
                collection_name=col_name,
                vectors_config=VectorParams(size=settings.EMBEDDING_DIMENSION, distance=Distance.COSINE),
            )
            logger.info("Recreated clean collection '%s' with dimension %d", col_name, settings.EMBEDDING_DIMENSION)
        except Exception as exc:
            logger.warning("Could not recreate collection '%s': %s", col_name, exc)

    # 3. Load Raw Documents
    raw_docs = load_sample_kb_documents(target_kb_dir)
    logger.info("Loaded %d raw documents from knowledge base directory.", len(raw_docs))
    if not raw_docs:
        logger.warning("No documents found in %s.", target_kb_dir)
        return {
            "status": "empty",
            "raw_documents_count": 0,
            "chunks_count": 0,
            "elapsed_seconds": round(time.time() - start_time, 2),
        }

    # 4. Semantic Text Chunking
    chunked_docs = split_documents(raw_docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    logger.info("Segmented %d raw documents into %d semantic chunks.", len(raw_docs), len(chunked_docs))

    # Category telemetry
    cat_counts: Dict[str, int] = {}
    for doc in chunked_docs:
        cat = doc.metadata.get("category", "GENERAL")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    for cat, count in cat_counts.items():
        logger.info("  - Category [%s]: %d chunks", cat, count)

    # 5. Embedding Vectorization & Batch Upsert
    indexed_count = upsert_documents(
        docs=chunked_docs,
        collection_name=col_name,
        client=q_client,
    )
    logger.info("Successfully indexed %d chunks into Qdrant collection '%s'.", indexed_count, col_name)

    elapsed = round(time.time() - start_time, 2)
    q_info = get_qdrant_info(client=q_client)

    # 6. Verification Diagnostic Probes
    verification_results: List[Dict[str, Any]] = []
    if verify:
        logger.info("\n--- Executing Self-Verification Diagnostic Probes ---")
        probe_queries = [
            ("年假带薪标准与病假申请手续", "HR"),
            ("采购金额超过50000元审批权限SOP", "PROCUREMENT"),
            ("IT办公设备借用与网络故障报修流程", "IT"),
        ]

        for q, expected_cat in probe_queries:
            results = search_similar_documents(
                query=q,
                top_k=1,
                collection_name=col_name,
                client=q_client,
            )
            if results:
                top_hit = results[0]
                hit_cat = top_hit.metadata.get("category", "UNKNOWN")
                hit_score = top_hit.metadata.get("score", 0.0)
                snippet = top_hit.page_content[:90].replace("\n", " ") + "..."
                logger.info(
                    "Probe Query: '%s' -> Top Hit [%s] (Score: %.4f): %s",
                    q,
                    hit_cat,
                    hit_score,
                    snippet,
                )
                verification_results.append(
                    {
                        "query": q,
                        "expected_category": expected_cat,
                        "hit_category": hit_cat,
                        "score": hit_score,
                        "snippet": snippet,
                    }
                )
            else:
                logger.warning("Probe Query: '%s' -> No results returned!", q)

    report = {
        "status": "success",
        "knowledge_dir": str(target_kb_dir),
        "collection_name": col_name,
        "raw_documents_count": len(raw_docs),
        "chunks_indexed": indexed_count,
        "category_breakdown": cat_counts,
        "elapsed_seconds": elapsed,
        "qdrant_info": q_info,
        "embedding_engine": get_embedding_engine_info(),
        "verification_probes": verification_results,
    }

    logger.info("\nIngestion Summary Report:")
    logger.info("  Total Raw Docs: %d", len(raw_docs))
    logger.info("  Total Chunks: %d", indexed_count)
    logger.info("  Total Points in Qdrant: %d", q_info.get("points_count", 0))
    logger.info("  Elapsed: %.2fs", elapsed)
    logger.info("=" * 60)

    return report


def main():
    parser = argparse.ArgumentParser(description="Ingest Enterprise Knowledge Base into Qdrant.")
    parser.add_argument("--kb-dir", type=str, default=None, help="Directory containing sample_kb docs")
    parser.add_argument("--collection", type=str, default=None, help="Target Qdrant collection name")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="Chunk overlap in characters")
    parser.add_argument("--recreate", action="store_true", help="Recreate Qdrant collection from scratch")
    parser.add_argument("--no-verify", action="store_true", help="Skip diagnostic verification probes")

    args = parser.parse_args()

    kb_path = Path(args.kb_dir) if args.kb_dir else None
    try:
        report = ingest_knowledge_base(
            kb_dir=kb_path,
            collection_name=args.collection,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            recreate=args.recreate,
            verify=not args.no_verify,
        )
        if report.get("status") != "success":
            sys.exit(1)
    except Exception as exc:
        logger.error("Knowledge Ingestion Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
