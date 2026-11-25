"""Celery Background Ingestion Tasks & Shared Document Processing Pipeline."""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import uuid

from langchain_core.documents import Document

from backend.core.knowledge_ledger import (
    record_uploaded_document,
    update_task_record,
)
from backend.core.multimodal_parser import MultimodalDocumentParser
from backend.rag.loader import (
    extract_metadata_from_filename,
    load_excel_document,
    load_markdown_document,
    load_pdf_document,
    load_text_document,
)
from backend.rag.splitter import split_documents
from backend.rag.vector_store import upsert_documents
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, str, Optional[Dict[str, Any]]], None]


def parse_and_load_file(file_path: Path) -> List[Document]:
    """Parses document into LangChain Document objects based on file suffix."""
    suffix = file_path.suffix.lower()
    if suffix == ".md":
        return load_markdown_document(file_path)
    if suffix == ".pdf":
        return load_pdf_document(file_path)
    if suffix in (".xlsx", ".xls"):
        return load_excel_document(file_path)
    return load_text_document(file_path)


def refresh_hybrid_retriever_docs(
    docs: List[Document],
    filename: Optional[str] = None,
) -> None:
    """Safely updates the global HybridRetriever BM25 index with newly indexed chunks."""
    if not docs:
        return
    try:
        from backend.rag.retriever import get_hybrid_retriever

        retriever = get_hybrid_retriever()
        if filename:
            retriever.sample_docs = [
                existing
                for existing in retriever.sample_docs
                if existing.metadata.get("filename") != filename
            ]
        retriever.sample_docs.extend(docs)
        if retriever.sample_docs:
            retriever.bm25_retriever.build_index(retriever.sample_docs)
    except Exception as exc:
        logger.warning("Failed to refresh HybridRetriever BM25 index for %s: %s", filename or "docs", exc)


def execute_document_ingestion(
    target_path: Path,
    *,
    category: Optional[str] = None,
    uploader: str = "admin",
    execution_mode: str = "sync",
    task_id: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
    refresh_bm25: bool = True,
) -> Dict[str, Any]:
    """Runs the full parse -> semantic split -> Qdrant upsert -> BM25 refresh pipeline."""
    if not target_path.exists():
        raise FileNotFoundError(f"Target document file not found: {target_path}")

    file_size = target_path.stat().st_size

    def _notify(stage: str, pct: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        if progress_callback is not None:
            progress_callback(stage, pct, message, extra)

    _notify("PARSING", 20, f"正在解析文档 {target_path.name}...", None)
    raw_docs = parse_and_load_file(target_path)

    cleaned_category = category.strip().upper() if isinstance(category, str) and category.strip() else None
    if cleaned_category == "AUTO":
        cleaned_category = None

    resolved_category = cleaned_category or (
        str(raw_docs[0].metadata.get("category", "GENERAL")).upper() if raw_docs else "GENERAL"
    )

    for doc in raw_docs:
        doc.metadata["filename"] = target_path.name
        doc.metadata["source"] = str(target_path)
        if cleaned_category:
            doc.metadata["category"] = cleaned_category

    _notify(
        "CHUNKING",
        55,
        f"已完成文本抽取（{len(raw_docs)} 段），正在执行语义切片...",
        {"raw_docs_count": len(raw_docs)},
    )
    docs = split_documents(raw_docs, chunk_size=500, chunk_overlap=50)

    _notify(
        "INDEXING",
        80,
        f"已切分 {len(docs)} 个语义片段，正在计算向量并写入 Qdrant...",
        {"chunks_count": len(docs)},
    )
    indexed_count = upsert_documents(docs) if docs else 0

    if refresh_bm25 and docs:
        refresh_hybrid_retriever_docs(docs, filename=target_path.name)

    effective_task_id = task_id or f"ingest-{uuid.uuid4().hex[:10]}"
    record_uploaded_document(
        filename=target_path.name,
        category=resolved_category,
        file_format=target_path.suffix.lstrip(".").lower(),
        size_bytes=file_size,
        chunks_indexed=indexed_count,
        last_task_id=effective_task_id,
        execution_mode=execution_mode,
        uploader=uploader,
        status="INDEXED",
    )

    return {
        "filename": target_path.name,
        "filepath": str(target_path),
        "size_bytes": file_size,
        "chunks_count": len(docs),
        "chunks_indexed": indexed_count,
        "category": resolved_category,
        "status": "COMPLETED",
        "progress": {"current": 100, "total": 100},
    }


def record_failed_document(
    target_path: Path,
    *,
    category: Optional[str] = None,
    uploader: str = "admin",
    execution_mode: str = "async",
    task_id: Optional[str] = None,
) -> None:
    """Marks an uploaded document as FAILED in the ledger when parsing/indexing aborts."""
    if not target_path.exists():
        return
    cleaned = category.strip().upper() if isinstance(category, str) and category.strip() else None
    if cleaned == "AUTO":
        cleaned = None
    inferred_cat = str(extract_metadata_from_filename(target_path).get("category", "GENERAL")).upper()
    record_uploaded_document(
        filename=target_path.name,
        category=cleaned or inferred_cat,
        file_format=target_path.suffix.lstrip(".").lower(),
        size_bytes=target_path.stat().st_size,
        chunks_indexed=0,
        last_task_id=task_id or f"failed-{uuid.uuid4().hex[:10]}",
        execution_mode=execution_mode,
        uploader=uploader,
        status="FAILED",
    )


@celery_app.task(name="async_ingest_document", bind=True)
def async_ingest_document(
    self,
    file_path_str: str,
    category: Optional[str] = None,
    uploader: str = "admin",
    execution_mode: str = "celery",
) -> Dict[str, Any]:
    """Celery Async Task for background document unpacking, semantic chunking,

    embedding extraction, Qdrant indexing, and BM25 index refresh.
    """
    target_path = Path(file_path_str)
    task_id = getattr(getattr(self, "request", None), "id", None)
    last_stage = "PARSING"

    def _celery_progress(
        stage: str,
        pct: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        nonlocal last_stage
        last_stage = stage
        meta: Dict[str, Any] = {
            "current": pct,
            "total": 100,
            "stage": stage,
            "status": message,
            "filename": target_path.name,
        }
        if extra:
            meta.update(extra)
        try:
            self.update_state(state="PROGRESS", meta=meta)
        except Exception:
            pass
        if task_id:
            update_task_record(
                task_id,
                status="PROGRESS",
                stage=stage,
                progress_current=pct,
                message=message,
            )

    try:
        result = execute_document_ingestion(
            target_path,
            category=category,
            uploader=uploader,
            execution_mode=execution_mode,
            task_id=task_id,
            progress_callback=_celery_progress,
            refresh_bm25=True,
        )
        if task_id:
            update_task_record(
                task_id,
                status="SUCCESS",
                stage="COMPLETED",
                progress_current=100,
                message=f"已完成 {target_path.name} 解析与 {result['chunks_indexed']} 条切片向量入库",
                result=result,
            )
        return result
    except Exception as exc:
        record_failed_document(
            target_path,
            category=category,
            uploader=uploader,
            execution_mode=execution_mode,
            task_id=task_id,
        )
        if task_id:
            update_task_record(
                task_id,
                status="FAILURE",
                stage="FAILED",
                message=f"异步解析任务失败: {exc}",
                error=str(exc),
                failed_stage=last_stage,
            )
        raise


@celery_app.task(name="async_parse_multimodal_file", bind=True)
def async_parse_multimodal_file(
    self,
    file_path_str: str,
    detect_columns: bool = True,
    merge_cross_page_tables: bool = True,
    index_to_vector_store: bool = False,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Celery Async Task for multimodal document parsing (PDF multi-column, cross-page tables, Excel multi-sheet)."""
    target_path = Path(file_path_str)
    if not target_path.exists():
        raise FileNotFoundError(f"Target document file not found: {file_path_str}")

    file_size = target_path.stat().st_size

    # Step 1: Progress state - parsing
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 30,
            "total": 100,
            "stage": "PARSING",
            "status": "Executing Multimodal Document Parser (columns & tables)...",
            "filename": target_path.name,
        },
    )

    parsed_chunks = MultimodalDocumentParser.parse_document(
        file_path=target_path,
        detect_columns=detect_columns,
        merge_cross_page_tables=merge_cross_page_tables,
    )

    docs = [c.to_langchain_document() for c in parsed_chunks]
    if category:
        for d in docs:
            d.metadata["category"] = category

    indexed_count = 0
    if index_to_vector_store and docs:
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 70,
                "total": 100,
                "stage": "INDEXING",
                "status": f"Indexing {len(docs)} multimodal chunks into Qdrant...",
                "filename": target_path.name,
            },
        )
        indexed_count = upsert_documents(docs)

    return {
        "filename": target_path.name,
        "filepath": str(target_path),
        "size_bytes": file_size,
        "chunks_count": len(docs),
        "table_chunks_count": sum(1 for c in parsed_chunks if c.chunk_type == "table"),
        "text_chunks_count": sum(1 for c in parsed_chunks if c.chunk_type == "text"),
        "chunks_indexed": indexed_count,
        "status": "COMPLETED",
        "progress": {"current": 100, "total": 100},
    }
