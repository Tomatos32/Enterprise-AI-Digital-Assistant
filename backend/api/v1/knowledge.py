"""FastAPI Knowledge Base Document Management, Upload & Hybrid Search Endpoints."""

import shutil
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, File, UploadFile, Form, Depends, Query
from langchain_core.documents import Document
from backend.core.exceptions import StandardResponse, AppException
from backend.core.rbac import require_role, RoleEnum, UserPayload
from backend.rag.loader import (
    load_markdown_document,
    load_pdf_document,
    load_excel_document,
    extract_metadata_from_filename,
)
from backend.rag.vector_store import upsert_documents
from backend.rag.retriever import HybridRetriever
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


@router.post("/upload", response_model=StandardResponse)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    is_async: bool = Form(False),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE]))
):
    """
    Receives an uploaded knowledge document, stores it in backend/data/.
    If is_async=True, dispatches Celery background ingestion task and returns task_id immediately.
    Otherwise parses chunks and indexes vectors into Qdrant synchronously.
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
                "uploader": getattr(current_user, "username", "unknown")
            }
        )

    # Synchronous Mode
    docs = parse_and_load_file(target_path)
    if category:
        for doc in docs:
            doc.metadata["category"] = category

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
            "uploader": getattr(current_user, "username", "unknown")
        }
    )


@router.post("/search", response_model=StandardResponse)
async def post_search_knowledge(
    req: SearchRequest,
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE]))
):
    """
    Performs Hybrid Retrieval (BM25 + Qdrant Dense Vector + RRF + Reranker)
    filtered by optional category.
    """
    retriever = get_hybrid_retriever()
    results = retriever.retrieve(
        query=req.query,
        top_k=req.top_k,
        category_filter=req.category_filter
    )
    
    data = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in results
    ]

    return StandardResponse(
        code=200,
        message="Hybrid retrieval completed",
        data={"query": req.query, "count": len(data), "results": data}
    )


@router.get("/search", response_model=StandardResponse)
async def get_search_knowledge(
    query: str = Query(..., description="Search query string"),
    top_k: int = Query(5, ge=1, le=20),
    category_filter: Optional[str] = Query(None),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE]))
):
    """
    GET shortcut for Hybrid Retrieval.
    """
    retriever = get_hybrid_retriever()
    results = retriever.retrieve(
        query=query,
        top_k=top_k,
        category_filter=category_filter
    )
    data = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in results
    ]

    return StandardResponse(
        code=200,
        message="Hybrid retrieval completed",
        data={"query": query, "count": len(data), "results": data}
    )
