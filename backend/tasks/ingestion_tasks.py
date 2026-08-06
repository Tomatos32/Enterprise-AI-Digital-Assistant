"""Celery Background Ingestion Tasks for Offline Document Processing & Indexing."""

from pathlib import Path
from typing import Optional, Dict, Any
from backend.tasks.celery_app import celery_app
from backend.rag.loader import (
    load_markdown_document,
    load_pdf_document,
    load_excel_document,
    extract_metadata_from_filename,
)
from backend.rag.vector_store import upsert_documents
from langchain_core.documents import Document


def parse_and_load_file(file_path: Path):
    """Parses document into chunk objects based on file suffix."""
    suffix = file_path.suffix.lower()
    if suffix == ".md":
        return load_markdown_document(file_path)
    elif suffix == ".pdf":
        return load_pdf_document(file_path)
    elif suffix in [".xlsx", ".xls"]:
        return load_excel_document(file_path)
    else:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        meta = extract_metadata_from_filename(file_path)
        meta["title"] = file_path.stem
        return [Document(page_content=text, metadata=meta)]


@celery_app.task(name="async_ingest_document", bind=True)
def async_ingest_document(self, file_path_str: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Celery Async Task for background document unpacking, chunking,
    embedding extraction, and indexing into Qdrant.
    """
    target_path = Path(file_path_str)
    if not target_path.exists():
        raise FileNotFoundError(f"Target document file not found: {file_path_str}")

    file_size = target_path.stat().st_size

    # Step 1: Update Task State to PROGRESS (25% - Loading file & parsing chunks)
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 25,
            "total": 100,
            "status": "Parsing and chunking document...",
            "filename": target_path.name,
        }
    )

    docs = parse_and_load_file(target_path)
    if category:
        for doc in docs:
            doc.metadata["category"] = category

    # Step 2: Update Task State to PROGRESS (60% - Embedding & Vectorizing)
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 60,
            "total": 100,
            "status": f"Parsed {len(docs)} chunks. Embedding and writing to Qdrant...",
            "filename": target_path.name,
            "chunks_count": len(docs),
        }
    )

    indexed_count = upsert_documents(docs)

    # Step 3: Complete Task
    return {
        "filename": target_path.name,
        "filepath": str(target_path),
        "size_bytes": file_size,
        "chunks_indexed": indexed_count,
        "category": category,
        "status": "COMPLETED",
        "progress": {"current": 100, "total": 100}
    }
