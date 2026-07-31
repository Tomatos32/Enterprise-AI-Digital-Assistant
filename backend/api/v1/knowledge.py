"""FastAPI Knowledge Base Document Management & File Upload Endpoints."""

import shutil
from pathlib import Path
from typing import List, Optional
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
from backend.rag.vector_store import upsert_documents, search_similar_documents

router = APIRouter()

DATA_DIR = Path("backend/data")


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
        # Generic text fallback
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        meta = extract_metadata_from_filename(file_path)
        return [Document(page_content=text, metadata=meta)]


@router.post("/upload", response_model=StandardResponse)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE]))
):
    """
    Receives an uploaded knowledge document, stores it in backend/data/,
    parses chunks, and indexes vectors into Qdrant.
    """
    if not file.filename:
        raise AppException(message="No file provided", status_code=400)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target_path = DATA_DIR / file.filename

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = target_path.stat().st_size

    # Load and parse document
    docs = parse_and_load_file(target_path)
    
    if category:
        for doc in docs:
            doc.metadata["category"] = category

    indexed_count = upsert_documents(docs)

    return StandardResponse(
        code=200,
        message="Knowledge document uploaded and indexed successfully",
        data={
            "filename": file.filename,
            "filepath": str(target_path),
            "size_bytes": file_size,
            "chunks_indexed": indexed_count,
            "uploader": getattr(current_user, "username", "unknown")
        }
    )


@router.get("/search", response_model=StandardResponse)
async def search_knowledge(
    query: str = Query(..., description="Search query string"),
    top_k: int = Query(5, ge=1, le=20),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE]))
):
    """
    Searches similar documents in Qdrant by query string.
    """
    results = search_similar_documents(query=query, top_k=top_k)
    data = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in results
    ]

    return StandardResponse(
        code=200,
        message="Similarity search completed",
        data={"query": query, "count": len(data), "results": data}
    )
