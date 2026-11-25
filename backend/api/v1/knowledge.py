"""FastAPI Knowledge Base Document Management, Upload, Sync & Hybrid Search Endpoints."""

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.exceptions import AppException, StandardResponse
from backend.core.knowledge_ledger import (
    ALLOWED_KNOWLEDGE_EXTENSIONS,
    MAX_UPLOAD_SIZE_BYTES,
    get_uploaded_documents_map,
    record_task_created,
    record_uploaded_document,
    update_task_record,
)
from backend.core.rbac import RoleEnum, UserPayload, require_role
from backend.rag.loader import extract_metadata_from_filename
from backend.rag.retriever import get_hybrid_retriever
from backend.rag.splitter import split_documents
from backend.rag.vector_store import get_qdrant_info, upsert_documents
from backend.tasks.celery_app import celery_app
from backend.tasks.ingestion_tasks import (
    async_ingest_document,
    execute_document_ingestion,
    parse_and_load_file,
    record_failed_document,
)

logger = logging.getLogger(__name__)

router = APIRouter()

DATA_DIR = Path("backend/data")
SAMPLE_KB_DIR = Path("docs/sample_kb")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Query search string")
    top_k: int = Field(5, ge=1, le=20, description="Top K documents to return")
    category_filter: Optional[str] = Field(None, description="Optional category filter (e.g. HR, PROCUREMENT)")


def _sanitize_and_validate_upload(raw_filename: Optional[str], content_bytes: bytes) -> Tuple[str, Path]:
    """Validates uploaded file extension, non-empty size, and path-traversal safety."""
    if not raw_filename or not raw_filename.strip():
        raise AppException(message="未检测到上传文件名，请重新选择文档", code=400)

    normalized_raw = raw_filename.replace("\\", "/").strip()
    if "\x00" in normalized_raw or ".." in normalized_raw.split("/"):
        raise AppException(message="文件名包含非法路径字符，已拒绝请求", code=400)

    safe_name = Path(normalized_raw).name.strip()
    if not safe_name or safe_name in (".", "..") or safe_name.startswith("."):
        raise AppException(message="上传文件名格式不合规，请提供有效文件名", code=400)

    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_KNOWLEDGE_EXTENSIONS:
        allowed_str = ", ".join(sorted(ALLOWED_KNOWLEDGE_EXTENSIONS))
        raise AppException(
            message=f"不支持的文档格式 '{suffix or '无后缀'}'，仅允许上传 {allowed_str}",
            code=400,
        )

    if len(content_bytes) == 0:
        raise AppException(message="上传文档内容为空 (0 字节)，无法建立索引", code=400)

    if len(content_bytes) > MAX_UPLOAD_SIZE_BYTES:
        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise AppException(message=f"文档大小超过单文件上限 ({max_mb} MB)", code=400)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    base_dir = DATA_DIR.resolve()
    target_path = (DATA_DIR / safe_name).resolve()
    if target_path.parent != base_dir:
        raise AppException(message="目标存储路径越界，已拦截非法路径", code=400)

    return safe_name, DATA_DIR / safe_name


def _ping_celery_worker() -> bool:
    """Checks if at least one Celery worker responds within a brief timeout."""
    try:
        res = celery_app.control.inspect(timeout=0.4).ping()
        return bool(res)
    except Exception:
        return False


async def _can_dispatch_celery() -> Tuple[bool, str, Optional[str]]:
    """Determines whether Celery eager/worker execution is available or should fall back locally."""
    if bool(getattr(celery_app.conf, "task_always_eager", False)):
        return True, "celery_eager", None

    broker_url = str(getattr(celery_app.conf, "broker_url", settings.REDIS_URL) or "")
    if not broker_url.startswith("redis"):
        return False, "async_fallback", "当前 Celery Broker 非在线 Redis 实例，已自动降级为应用内后台异步队列"

    parsed = urlparse(broker_url)
    host = parsed.hostname or settings.REDIS_HOST
    port = parsed.port or settings.REDIS_PORT

    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=0.35,
        )
        writer.close()
        await writer.wait_closed()
    except Exception as exc:
        return (
            False,
            "async_fallback",
            f"Redis Broker ({host}:{port}) 未在线 ({type(exc).__name__})，已平滑降级为后台异步队列",
        )

    worker_alive = await asyncio.to_thread(_ping_celery_worker)
    if not worker_alive:
        return (
            False,
            "async_fallback",
            "Redis 已连通但未检测到在线 Celery Worker 进程，已平滑降级为后台异步队列",
        )

    return True, "celery_worker", None


async def _run_fallback_ingestion_task(
    task_id: str,
    target_path: Path,
    category: Optional[str],
    uploader: str,
) -> None:
    """Executes document ingestion in FastAPI BackgroundTasks when Celery Worker is offline."""
    last_stage = "PARSING"
    loop = asyncio.get_running_loop()

    def _thread_progress(
        stage: str,
        pct: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        nonlocal last_stage
        last_stage = stage
        update_task_record(
            task_id,
            status="PROGRESS",
            stage=stage,
            progress_current=pct,
            message=message,
        )

    try:
        update_task_record(
            task_id,
            status="PROGRESS",
            stage="PARSING",
            progress_current=15,
            message=f"后台异步引擎已接管 {target_path.name}，开始解析...",
        )
        result = await loop.run_in_executor(
            None,
            lambda: execute_document_ingestion(
                target_path,
                category=category,
                uploader=uploader,
                execution_mode="async_fallback",
                task_id=task_id,
                progress_callback=_thread_progress,
                refresh_bm25=True,
            ),
        )
        update_task_record(
            task_id,
            status="SUCCESS",
            stage="COMPLETED",
            progress_current=100,
            message=f"已完成 {target_path.name} 解析与 {result['chunks_indexed']} 条切片向量入库",
            result=result,
        )
    except Exception as exc:
        logger.warning("Fallback async ingestion failed for %s: %s", target_path, exc)
        record_failed_document(
            target_path,
            category=category,
            uploader=uploader,
            execution_mode="async_fallback",
            task_id=task_id,
        )
        update_task_record(
            task_id,
            status="FAILURE",
            stage="FAILED",
            message=f"异步降级入库失败: {exc}",
            error=str(exc),
            failed_stage=last_stage,
        )


def _collect_status_and_files() -> Dict[str, Any]:
    """Collects Qdrant telemetry and indexed file lists (executed off the event loop)."""
    q_info = get_qdrant_info()
    builtin_files: List[str] = []
    if SAMPLE_KB_DIR.exists():
        for p in sorted(SAMPLE_KB_DIR.rglob("*")):
            if p.is_file() and p.suffix.lower() in ALLOWED_KNOWLEDGE_EXTENSIONS:
                builtin_files.append(p.name)

    uploaded_files: List[str] = []
    if DATA_DIR.exists():
        for p in sorted(DATA_DIR.iterdir()):
            if p.is_file() and p.suffix.lower() in ALLOWED_KNOWLEDGE_EXTENSIONS:
                uploaded_files.append(p.name)

    return {
        "status": q_info.get("status", "healthy"),
        "client_mode": q_info.get("client_mode"),
        "storage_location": q_info.get("storage_location"),
        "collection_name": q_info.get("collection_name"),
        "collection_exists": q_info.get("collection_exists"),
        "points_count": q_info.get("points_count", 0),
        "vector_size": q_info.get("vector_size", 1024),
        "embedding_engine": q_info.get("embedding_engine"),
        "sample_kb_files": builtin_files,
        "sample_kb_file_count": len(builtin_files),
        "uploaded_files": uploaded_files,
        "uploaded_file_count": len(uploaded_files),
        "total_documents_count": len(builtin_files) + len(uploaded_files),
    }


def _collect_documents_inventory() -> Dict[str, Any]:
    """Builds detailed inventory of built-in sample_kb and admin-uploaded knowledge documents."""
    uploaded_meta_map = get_uploaded_documents_map()
    documents: List[Dict[str, Any]] = []
    category_counts: Dict[str, int] = {}

    if SAMPLE_KB_DIR.exists():
        for p in sorted(SAMPLE_KB_DIR.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in ALLOWED_KNOWLEDGE_EXTENSIONS:
                continue
            stat = p.stat()
            inferred = extract_metadata_from_filename(p)
            category = str(inferred.get("category", "GENERAL")).upper()
            category_counts[category] = category_counts.get(category, 0) + 1
            documents.append(
                {
                    "filename": p.name,
                    "source_type": "builtin",
                    "format": p.suffix.lstrip(".").lower(),
                    "category": category,
                    "size_bytes": stat.st_size,
                    "chunks_indexed": None,
                    "execution_mode": "builtin_kb",
                    "uploader": "system",
                    "status": "INDEXED",
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    "relative_path": str(p.relative_to(SAMPLE_KB_DIR)).replace("\\", "/"),
                }
            )

    if DATA_DIR.exists():
        for p in sorted(DATA_DIR.iterdir()):
            if not p.is_file() or p.suffix.lower() not in ALLOWED_KNOWLEDGE_EXTENSIONS:
                continue
            stat = p.stat()
            recorded = uploaded_meta_map.get(p.name, {})
            inferred = extract_metadata_from_filename(p)
            category = str(recorded.get("category") or inferred.get("category", "GENERAL")).upper()
            category_counts[category] = category_counts.get(category, 0) + 1
            documents.append(
                {
                    "filename": p.name,
                    "source_type": "uploaded",
                    "format": p.suffix.lstrip(".").lower(),
                    "category": category,
                    "size_bytes": recorded.get("size_bytes", stat.st_size),
                    "chunks_indexed": recorded.get("chunks_indexed"),
                    "last_task_id": recorded.get("last_task_id"),
                    "execution_mode": recorded.get("execution_mode", "uploaded_disk"),
                    "uploader": recorded.get("uploader", "admin"),
                    "status": recorded.get("status", "INDEXED"),
                    "updated_at": recorded.get("updated_at")
                    or datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    "relative_path": f"backend/data/{p.name}",
                }
            )

    builtin_count = sum(1 for d in documents if d["source_type"] == "builtin")
    uploaded_count = sum(1 for d in documents if d["source_type"] == "uploaded")

    return {
        "documents": documents,
        "total_count": len(documents),
        "builtin_count": builtin_count,
        "uploaded_count": uploaded_count,
        "category_breakdown": category_counts,
    }


def _execute_full_sync(recreate: bool, uploader: str, task_id: str) -> Dict[str, Any]:
    """Synchronizes docs/sample_kb plus uploaded files in DATA_DIR and refreshes HybridRetriever."""
    from backend.scripts.ingest_knowledge import ingest_knowledge_base

    report = ingest_knowledge_base(recreate=recreate, verify=True)

    uploaded_meta_map = get_uploaded_documents_map()
    uploaded_chunks: List[Document] = []
    uploaded_files_reindexed = 0

    if DATA_DIR.exists():
        for p in sorted(DATA_DIR.iterdir()):
            if not p.is_file() or p.suffix.lower() not in ALLOWED_KNOWLEDGE_EXTENSIONS:
                continue
            try:
                raw_docs = parse_and_load_file(p)
                recorded = uploaded_meta_map.get(p.name, {})
                cat = recorded.get("category")
                for doc in raw_docs:
                    doc.metadata["filename"] = p.name
                    doc.metadata["source"] = str(p)
                    if cat:
                        doc.metadata["category"] = str(cat).upper()
                chunks = split_documents(raw_docs, chunk_size=500, chunk_overlap=50)
                if chunks:
                    indexed = upsert_documents(chunks)
                    uploaded_chunks.extend(chunks)
                    uploaded_files_reindexed += 1
                    record_uploaded_document(
                        filename=p.name,
                        category=str(cat or chunks[0].metadata.get("category", "GENERAL")).upper(),
                        file_format=p.suffix.lstrip(".").lower(),
                        size_bytes=p.stat().st_size,
                        chunks_indexed=indexed,
                        last_task_id=task_id,
                        execution_mode="sync_rebuild" if recreate else "sync",
                        uploader=str(recorded.get("uploader") or uploader),
                        status="INDEXED",
                    )
            except Exception as exc:
                logger.warning("Skipped re-indexing uploaded file %s during sync: %s", p.name, exc)

    retriever = get_hybrid_retriever(force_refresh=True)
    if uploaded_chunks:
        retriever.sample_docs.extend(uploaded_chunks)
        retriever.bm25_retriever.build_index(retriever.sample_docs)

    q_info = get_qdrant_info()
    report["qdrant_info"] = q_info
    report["recreate"] = recreate
    report["task_id"] = task_id
    report["uploaded_reindexed_files"] = uploaded_files_reindexed
    report["uploaded_reindexed_chunks"] = len(uploaded_chunks)
    return report


@router.get("/status", response_model=StandardResponse)
async def get_knowledge_status(
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE])),
):
    """Returns comprehensive runtime observability and diagnostic status of the knowledge base."""
    data = await asyncio.to_thread(_collect_status_and_files)
    return StandardResponse(
        code=200,
        message="Knowledge base status retrieved successfully",
        data=data,
    )


@router.get("/documents", response_model=StandardResponse)
async def list_knowledge_documents(
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Admin-only endpoint listing all built-in and uploaded knowledge base documents."""
    inventory = await asyncio.to_thread(_collect_documents_inventory)
    return StandardResponse(
        code=200,
        message="Knowledge documents inventory retrieved successfully",
        data=inventory,
    )


@router.post("/sync", response_model=StandardResponse)
async def sync_knowledge_base(
    recreate: bool = Query(False, description="Whether to recreate collection from scratch"),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Admin-only endpoint triggering re-ingestion of sample_kb & uploaded files and refreshing HybridRetriever."""
    uploader_name = getattr(current_user, "username", "admin")
    task_id = f"sync-{uuid.uuid4().hex[:12]}"
    sync_label = "全量重建同步 (sample_kb + 上传文档)" if recreate else "增量校验同步 (sample_kb + 上传文档)"

    record_task_created(
        task_id=task_id,
        task_type="sync",
        filename=sync_label,
        execution_mode="sync_rebuild" if recreate else "sync",
        uploader=uploader_name,
        category="ALL",
        status="PROGRESS",
        stage="INDEXING",
        message=f"正在执行{sync_label}...",
        progress_current=50,
    )

    try:
        report = await asyncio.to_thread(_execute_full_sync, recreate, uploader_name, task_id)
        total_points = report.get("qdrant_info", {}).get("points_count", 0)
        update_task_record(
            task_id,
            status="SUCCESS",
            stage="COMPLETED",
            progress_current=100,
            message=f"{sync_label}完成，当前库内共 {total_points} 条向量切片",
            result=report,
        )
        return StandardResponse(
            code=200,
            message="Knowledge base synced and indexed successfully",
            data=report,
        )
    except Exception as exc:
        update_task_record(
            task_id,
            status="FAILURE",
            stage="FAILED",
            message=f"知识库同步失败: {exc}",
            error=str(exc),
            failed_stage="INDEXING",
        )
        raise AppException(message=f"知识库同步失败: {exc}", code=500) from exc


@router.post("/upload", response_model=StandardResponse)
async def upload_knowledge_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    is_async: bool = Form(False),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Admin-only endpoint receiving a validated knowledge document and indexing it sync or async."""
    content_bytes = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    safe_name, target_path = _sanitize_and_validate_upload(file.filename, content_bytes)
    existed_before = target_path.exists()
    await asyncio.to_thread(target_path.write_bytes, content_bytes)

    file_size = len(content_bytes)
    uploader_name = getattr(current_user, "username", "admin")

    if is_async:
        can_celery, exec_mode, fallback_reason = await _can_dispatch_celery()
        fallback_task_id: Optional[str] = None
        if can_celery:
            task_id = str(uuid.uuid4())
            record_task_created(
                task_id=task_id,
                task_type="upload",
                filename=safe_name,
                filepath=str(target_path),
                size_bytes=file_size,
                category=category,
                execution_mode=exec_mode,
                uploader=uploader_name,
                status="PENDING",
                stage="QUEUED",
                message="任务已投递至 Celery 异步解析队列",
                progress_current=0,
            )
            try:
                async_ingest_document.apply_async(
                    args=[str(target_path), category],
                    kwargs={"uploader": uploader_name, "execution_mode": exec_mode},
                    task_id=task_id,
                )
                return StandardResponse(
                    code=200,
                    message="Async document ingestion task submitted",
                    data={
                        "filename": safe_name,
                        "filepath": str(target_path),
                        "size_bytes": file_size,
                        "category": category,
                        "task_id": task_id,
                        "status": "SUBMITTED",
                        "is_async": True,
                        "execution_mode": exec_mode,
                        "fallback_reason": None,
                        "uploader": uploader_name,
                    },
                )
            except Exception as exc:
                fallback_task_id = task_id
                fallback_reason = f"Celery 投递异常 ({type(exc).__name__})，已切换为后台异步任务队列"
                logger.warning("Celery apply_async failed for %s, falling back locally: %s", safe_name, exc)

        fallback_task_id = fallback_task_id or f"fb-{uuid.uuid4().hex[:12]}"
        record_task_created(
            task_id=fallback_task_id,
            task_type="upload",
            filename=safe_name,
            filepath=str(target_path),
            size_bytes=file_size,
            category=category,
            execution_mode="async_fallback",
            fallback_reason=fallback_reason,
            uploader=uploader_name,
            status="PENDING",
            stage="QUEUED",
            message="任务已加入应用内后台异步队列，等待解析",
            progress_current=5,
        )
        background_tasks.add_task(
            _run_fallback_ingestion_task,
            fallback_task_id,
            target_path,
            category,
            uploader_name,
        )
        return StandardResponse(
            code=200,
            message="Async document ingestion task submitted via local fallback queue",
            data={
                "filename": safe_name,
                "filepath": str(target_path),
                "size_bytes": file_size,
                "category": category,
                "task_id": fallback_task_id,
                "status": "SUBMITTED",
                "is_async": True,
                "execution_mode": "async_fallback",
                "fallback_reason": fallback_reason,
                "uploader": uploader_name,
            },
        )

    # Synchronous Fast Ingestion Mode
    sync_task_id = f"sync-{uuid.uuid4().hex[:12]}"
    record_task_created(
        task_id=sync_task_id,
        task_type="upload",
        filename=safe_name,
        filepath=str(target_path),
        size_bytes=file_size,
        category=category,
        execution_mode="sync",
        uploader=uploader_name,
        status="PROGRESS",
        stage="PARSING",
        message=f"正在同步解析文档 {safe_name}...",
        progress_current=20,
    )

    def _sync_progress(stage: str, pct: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        update_task_record(sync_task_id, status="PROGRESS", stage=stage, progress_current=pct, message=message)

    try:
        result = await asyncio.to_thread(
            execute_document_ingestion,
            target_path,
            category=category,
            uploader=uploader_name,
            execution_mode="sync",
            task_id=sync_task_id,
            progress_callback=_sync_progress,
            refresh_bm25=True,
        )
        update_task_record(
            sync_task_id,
            status="SUCCESS",
            stage="COMPLETED",
            progress_current=100,
            message=f"已完成 {safe_name} 同步解析与 {result['chunks_indexed']} 条切片入库",
            result=result,
        )
        return StandardResponse(
            code=200,
            message="Knowledge document uploaded and indexed successfully",
            data={
                "filename": safe_name,
                "filepath": str(target_path),
                "size_bytes": file_size,
                "category": result["category"],
                "chunks_indexed": result["chunks_indexed"],
                "chunks_count": result["chunks_count"],
                "task_id": sync_task_id,
                "status": "COMPLETED",
                "execution_mode": "sync",
                "is_async": False,
                "uploader": uploader_name,
            },
        )
    except Exception as exc:
        if not existed_before:
            target_path.unlink(missing_ok=True)
        else:
            record_failed_document(
                target_path,
                category=category,
                uploader=uploader_name,
                execution_mode="sync",
                task_id=sync_task_id,
            )
        update_task_record(
            sync_task_id,
            status="FAILURE",
            stage="FAILED",
            message=f"同步解析入库失败: {exc}",
            error=str(exc),
            failed_stage="INDEXING",
        )
        raise AppException(message=f"文档解析或向量入库失败: {exc}", code=400) from exc


def _run_hybrid_search(
    query: str,
    top_k: int,
    category_filter: Optional[str],
) -> List[Dict[str, Any]]:
    """Executes HybridRetriever lookup off the event loop (including cold-start BM25 build)."""
    retriever = get_hybrid_retriever()
    results = retriever.retrieve(
        query=query,
        top_k=top_k,
        category_filter=category_filter,
    )
    return [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]


@router.post("/search", response_model=StandardResponse)
async def post_search_knowledge(
    req: SearchRequest,
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE])),
):
    """Performs Hybrid Retrieval (BM25 + Qdrant Dense Vector + RRF + Reranker) filtered by optional category."""
    data = await asyncio.to_thread(_run_hybrid_search, req.query, req.top_k, req.category_filter)

    return StandardResponse(
        code=200,
        message="Hybrid retrieval completed",
        data={"query": req.query, "count": len(data), "results": data},
    )


@router.get("/search", response_model=StandardResponse)
async def get_search_knowledge(
    query: str = Query(..., description="Search query string"),
    top_k: int = Query(5, ge=1, le=20),
    category_filter: Optional[str] = Query(None),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE])),
):
    """GET shortcut for Hybrid Retrieval."""
    data = await asyncio.to_thread(_run_hybrid_search, query, top_k, category_filter)

    return StandardResponse(
        code=200,
        message="Hybrid retrieval completed",
        data={"query": query, "count": len(data), "results": data},
    )
