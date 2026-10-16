"""FastAPI Knowledge Base Document Management, Upload & Hybrid Search Endpoints."""

from pathlib import Path
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from backend.core.exceptions import AppException, StandardResponse
from backend.core.rbac import RoleEnum, UserPayload, require_role
from backend.rag.loader import (
    extract_metadata_from_filename,
    load_excel_document,
    load_markdown_document,
    load_pdf_document,
)
from backend.rag.retriever import HybridRetriever
from backend.rag.splitter import split_documents
from backend.rag.vector_store import get_qdrant_info, upsert_documents
from backend.tasks.ingestion_tasks import async_ingest_document

router = APIRouter()

DATA_DIR = Path("backend/data")
_hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    """Singleton getter for HybridRetriever engine."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever


class SearchRequest(BaseModel):
    query: str = Field(..., description="Query search string")
    top_k: int = Field(5, ge=1, le=20, description="Top K documents to return")
    category_filter: Optional[str] = Field(None, description="Optional category filter (e.g. HR, PROCUREMENT)")


def parse_and_load_file(file_path: Path) -> List[Document]:
    """Determines file type and parses it into Document chunks."""
    suffix = file_path.suffix.lower()
    if suffix == ".md":
        return load_markdown_document(file_path)
    elif suffix == ".pdf":
        return load_pdf_document(file_path)
    elif suffix in [".xlsx", ".xls"]:
        return load_excel_document(file_path)
    elif suffix in [".txt", ".log"]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        meta = extract_metadata_from_filename(file_path)
        meta["title"] = file_path.stem
        return [Document(page_content=text, metadata=meta)]
    else:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        meta = extract_metadata_from_filename(file_path)
        return [Document(page_content=text, metadata=meta)]


@router.get("/status", response_model=StandardResponse)
async def get_knowledge_status(
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE])),
):
    """Returns comprehensive runtime observability and diagnostic status of the knowledge base

    including vector count, storage mode, embedding engine, and indexed file catalogue.
    """
    q_info = get_qdrant_info()
    sample_kb_path = Path("docs/sample_kb")
    indexed_files = []
    if sample_kb_path.exists():
        for p in sample_kb_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in [".md", ".pdf", ".xlsx", ".xls"]:
                indexed_files.append(p.name)

    return StandardResponse(
        code=200,
        message="Knowledge base status retrieved successfully",
        data={
            "status": q_info.get("status", "healthy"),
            "client_mode": q_info.get("client_mode"),
            "storage_location": q_info.get("storage_location"),
            "collection_name": q_info.get("collection_name"),
            "collection_exists": q_info.get("collection_exists"),
            "points_count": q_info.get("points_count", 0),
            "vector_size": q_info.get("vector_size", 1024),
            "embedding_engine": q_info.get("embedding_engine"),
            "sample_kb_files": indexed_files,
            "sample_kb_file_count": len(indexed_files),
        },
    )


@router.post("/sync", response_model=StandardResponse)
async def sync_knowledge_base(
    recreate: bool = Query(False, description="Whether to recreate collection from scratch"),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER])),
):
    """Triggers on-demand re-ingestion of the sample knowledge base into Qdrant."""
    from backend.scripts.ingest_knowledge import ingest_knowledge_base

    report = ingest_knowledge_base(recreate=recreate, verify=True)
    return StandardResponse(code=200, message="Knowledge base synced and indexed successfully", data=report)


@router.post("/upload", response_model=StandardResponse)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    is_async: bool = Form(False),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE])),
):
    """Receives an uploaded knowledge document, stores it in backend/data/.

    If is_async=True, dispatches Celery background ingestion task and returns task_id immediately.
    Otherwise parses chunks, splits semantically, and indexes vectors into Qdrant synchronously.
    """
    if not file.filename:
        raise AppException(message="No file provided", status_code=400)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target_path = DATA_DIR / file.filename

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = target_path.stat().st_size

    # Async Ingestion Task Mode
    if is_async:
        task = async_ingest_document.delay(str(target_path), category)
        return StandardResponse(
            code=200,
            message="Async document ingestion task submitted",
            data={
                "filename": file.filename,
                "filepath": str(target_path),
                "size_bytes": file_size,
                "task_id": task.id,
                "status": "SUBMITTED",
                "is_async": True,
                "uploader": getattr(current_user, "username", "unknown"),
            },
        )

    # Synchronous Mode
    raw_docs = parse_and_load_file(target_path)
    if category:
        for doc in raw_docs:
            doc.metadata["category"] = category

    # Apply semantic chunking
    docs = split_documents(raw_docs, chunk_size=500, chunk_overlap=50)
    indexed_count = upsert_documents(docs)

    # Refresh BM25 index on new uploads
    retriever = get_hybrid_retriever()
    retriever.sample_docs.extend(docs)
    retriever.bm25_retriever.build_index(retriever.sample_docs)

    return StandardResponse(
        code=200,
        message="Knowledge document uploaded and indexed successfully",
        data={
            "filename": file.filename,
            "filepath": str(target_path),
            "size_bytes": file_size,
            "chunks_indexed": indexed_count,
            "is_async": False,
            "uploader": getattr(current_user, "username", "unknown"),
        },
    )


@router.post("/search", response_model=StandardResponse)
async def post_search_knowledge(
    req: SearchRequest,
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE])),
):
    """Performs Hybrid Retrieval (BM25 + Qdrant Dense Vector + RRF + Reranker)

    filtered by optional category.
    """
    retriever = get_hybrid_retriever()
    results = retriever.retrieve(query=req.query, top_k=req.top_k, category_filter=req.category_filter)

    data = [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]

    return StandardResponse(
        code=200, message="Hybrid retrieval completed", data={"query": req.query, "count": len(data), "results": data}
    )


@router.get("/search", response_model=StandardResponse)
async def get_search_knowledge(
    query: str = Query(..., description="Search query string"),
    top_k: int = Query(5, ge=1, le=20),
    category_filter: Optional[str] = Query(None),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE])),
):
    """GET shortcut for Hybrid Retrieval."""
    retriever = get_hybrid_retriever()
    results = retriever.retrieve(query=query, top_k=top_k, category_filter=category_filter)
    data = [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]

    return StandardResponse(
        code=200, message="Hybrid retrieval completed", data={"query": query, "count": len(data), "results": data}
    )
