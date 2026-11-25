"""Thread-Safe Persistent Ledger for Knowledge Document Uploads & Ingestion Tasks."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LEDGER_PATH = Path("logs/knowledge_tasks_ledger.json")
ALLOWED_KNOWLEDGE_EXTENSIONS = {".md", ".pdf", ".xlsx", ".xls", ".txt"}
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB per file
MAX_TASKS_HISTORY = 80

PIPELINE_STAGES: List[Tuple[str, str]] = [
    ("QUEUED", "任务排队"),
    ("PARSING", "文档解析"),
    ("CHUNKING", "语义切片"),
    ("INDEXING", "向量入库"),
    ("COMPLETED", "完成入库"),
]

STAGE_LABEL_MAP: Dict[str, str] = {
    "QUEUED": "任务排队等待中",
    "PARSING": "正在解析文档版式与文本",
    "CHUNKING": "正在执行语义切片与分类标注",
    "INDEXING": "正在向量化并写入 Qdrant 索引",
    "COMPLETED": "向量入库与索引刷新完成",
    "FAILED": "任务执行失败",
}

_ledger_lock = threading.RLock()
_loaded_path: Optional[Path] = None
_ledger_cache: Dict[str, Any] = {"tasks": [], "documents": {}}


def _utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _ensure_loaded_locked() -> None:
    """Loads persisted ledger JSON into memory if path changed or not yet loaded."""
    global _loaded_path, _ledger_cache
    if _loaded_path == LEDGER_PATH:
        return

    _loaded_path = LEDGER_PATH
    if not LEDGER_PATH.exists():
        _ledger_cache = {"tasks": [], "documents": {}}
        return

    try:
        raw = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            tasks = raw.get("tasks")
            documents = raw.get("documents")
            _ledger_cache = {
                "tasks": tasks if isinstance(tasks, list) else [],
                "documents": documents if isinstance(documents, dict) else {},
            }
            return
    except Exception as exc:
        logger.warning("Failed to load knowledge tasks ledger from %s: %s", LEDGER_PATH, exc)

    _ledger_cache = {"tasks": [], "documents": {}}


def _persist_locked() -> None:
    """Atomically writes ledger cache to disk without crashing callers on I/O failure."""
    try:
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(_ledger_cache, ensure_ascii=False, indent=2)
        tmp_file = LEDGER_PATH.with_suffix(".tmp")
        tmp_file.write_text(payload, encoding="utf-8")
        tmp_file.replace(LEDGER_PATH)
    except OSError as exc:
        logger.warning("Failed to persist knowledge tasks ledger to %s: %s", LEDGER_PATH, exc)


def reset_ledger_cache() -> None:
    """Clears in-memory ledger cache (primarily for isolated unit test runs)."""
    global _loaded_path, _ledger_cache
    with _ledger_lock:
        _loaded_path = None
        _ledger_cache = {"tasks": [], "documents": {}}


def infer_stage_from_state(
    state: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, int]:
    """Maps Celery/task state and metadata into standardized (stage, stage_label, percentage)."""
    normalized = (state or "PENDING").upper()
    meta = meta if isinstance(meta, dict) else {}

    if normalized == "SUCCESS":
        return "COMPLETED", STAGE_LABEL_MAP["COMPLETED"], 100
    if normalized == "FAILURE":
        return "FAILED", STAGE_LABEL_MAP["FAILED"], int(meta.get("current", 0) or 0)
    if normalized == "PENDING":
        return "QUEUED", STAGE_LABEL_MAP["QUEUED"], 0

    explicit_stage = str(meta.get("stage", "")).upper()
    current_pct = int(meta.get("current", 50) or 50)

    if explicit_stage in STAGE_LABEL_MAP:
        return explicit_stage, STAGE_LABEL_MAP[explicit_stage], current_pct
    if current_pct >= 80:
        return "INDEXING", STAGE_LABEL_MAP["INDEXING"], current_pct
    if current_pct >= 50:
        return "CHUNKING", STAGE_LABEL_MAP["CHUNKING"], current_pct
    if current_pct >= 15:
        return "PARSING", STAGE_LABEL_MAP["PARSING"], current_pct
    return "QUEUED", STAGE_LABEL_MAP["QUEUED"], current_pct


def build_pipeline_steps(
    stage: str,
    status: str,
    failed_stage: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Builds the 5-stage StatusMark pipeline representation for frontend tracking."""
    norm_status = (status or "PENDING").upper()
    norm_stage = (stage or "QUEUED").upper()
    stage_keys = [key for key, _ in PIPELINE_STAGES]

    if norm_status == "SUCCESS" or norm_stage == "COMPLETED":
        return [{"key": key, "label": label, "status": "success"} for key, label in PIPELINE_STAGES]

    if norm_status == "FAILURE" or norm_stage == "FAILED":
        fail_key = (failed_stage or "INDEXING").upper()
        fail_idx = stage_keys.index(fail_key) if fail_key in stage_keys else len(stage_keys) - 1
        steps: List[Dict[str, str]] = []
        for idx, (key, label) in enumerate(PIPELINE_STAGES):
            if idx < fail_idx:
                steps.append({"key": key, "label": label, "status": "success"})
            elif idx == fail_idx:
                steps.append(
                    {
                        "key": "FAILED" if key == "COMPLETED" else key,
                        "label": "失败中断" if key == "COMPLETED" else f"{label}失败",
                        "status": "danger",
                    }
                )
            else:
                steps.append(
                    {
                        "key": key,
                        "label": "失败中断" if key == "COMPLETED" else label,
                        "status": "idle",
                    }
                )
        return steps

    if norm_status == "PENDING" or norm_stage == "QUEUED":
        return [
            {"key": key, "label": label, "status": "running" if idx == 0 else "idle"}
            for idx, (key, label) in enumerate(PIPELINE_STAGES)
        ]

    active_idx = stage_keys.index(norm_stage) if norm_stage in stage_keys else 1
    return [
        {
            "key": key,
            "label": label,
            "status": "success" if idx < active_idx else ("running" if idx == active_idx else "idle"),
        }
        for idx, (key, label) in enumerate(PIPELINE_STAGES)
    ]


def record_task_created(
    *,
    task_id: str,
    task_type: str,
    filename: str,
    execution_mode: str,
    uploader: str,
    category: Optional[str] = None,
    filepath: Optional[str] = None,
    size_bytes: int = 0,
    fallback_reason: Optional[str] = None,
    status: str = "PENDING",
    stage: str = "QUEUED",
    message: str = "任务已加入调度队列",
    progress_current: int = 0,
) -> Dict[str, Any]:
    """Inserts a new task record at the head of the persistent ledger."""
    now = _utc_now_iso()
    record: Dict[str, Any] = {
        "task_id": task_id,
        "task_type": task_type,
        "filename": filename,
        "filepath": filepath,
        "size_bytes": size_bytes,
        "category": category,
        "execution_mode": execution_mode,
        "fallback_reason": fallback_reason,
        "uploader": uploader,
        "status": status,
        "stage": stage,
        "stage_label": STAGE_LABEL_MAP.get(stage, message),
        "progress": {"current": progress_current, "total": 100},
        "message": message,
        "ready": status in ("SUCCESS", "FAILURE"),
        "successful": status == "SUCCESS",
        "result": None,
        "error": None,
        "failed_stage": None,
        "created_at": now,
        "updated_at": now,
    }
    record["steps"] = build_pipeline_steps(stage, status)

    with _ledger_lock:
        _ensure_loaded_locked()
        tasks: List[Dict[str, Any]] = [
            item for item in _ledger_cache["tasks"] if item.get("task_id") != task_id
        ]
        tasks.insert(0, record)
        _ledger_cache["tasks"] = tasks[:MAX_TASKS_HISTORY]
        _persist_locked()

    return dict(record)


def update_task_record(
    task_id: str,
    *,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    progress_current: Optional[int] = None,
    message: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    failed_stage: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Updates an existing task record's stage, progress, and outcome."""
    with _ledger_lock:
        _ensure_loaded_locked()
        target: Optional[Dict[str, Any]] = None
        for item in _ledger_cache["tasks"]:
            if item.get("task_id") == task_id:
                target = item
                break

        if target is None:
            return None

        if status is not None:
            target["status"] = status
        if stage is not None:
            target["stage"] = stage
            target["stage_label"] = STAGE_LABEL_MAP.get(stage, target.get("stage_label", ""))
        if progress_current is not None:
            target["progress"] = {"current": int(progress_current), "total": 100}
        if message is not None:
            target["message"] = message
        if result is not None:
            target["result"] = result
        if error is not None:
            target["error"] = error
        if failed_stage is not None:
            target["failed_stage"] = failed_stage

        cur_status = str(target.get("status", "PENDING"))
        cur_stage = str(target.get("stage", "QUEUED"))
        target["ready"] = cur_status in ("SUCCESS", "FAILURE")
        target["successful"] = cur_status == "SUCCESS"
        target["steps"] = build_pipeline_steps(
            cur_stage,
            cur_status,
            failed_stage=target.get("failed_stage"),
        )
        target["updated_at"] = _utc_now_iso()
        _persist_locked()
        return dict(target)


def get_task_record(task_id: str) -> Optional[Dict[str, Any]]:
    """Returns a copy of a stored task record by task_id if present."""
    with _ledger_lock:
        _ensure_loaded_locked()
        for item in _ledger_cache["tasks"]:
            if item.get("task_id") == task_id:
                copy_item = dict(item)
                copy_item["steps"] = build_pipeline_steps(
                    str(copy_item.get("stage", "QUEUED")),
                    str(copy_item.get("status", "PENDING")),
                    failed_stage=copy_item.get("failed_stage"),
                )
                return copy_item
    return None


def list_task_records(limit: int = 30) -> List[Dict[str, Any]]:
    """Lists recent ingestion and synchronization tasks."""
    with _ledger_lock:
        _ensure_loaded_locked()
        items: List[Dict[str, Any]] = []
        for item in _ledger_cache["tasks"][:limit]:
            copy_item = dict(item)
            copy_item["steps"] = build_pipeline_steps(
                str(copy_item.get("stage", "QUEUED")),
                str(copy_item.get("status", "PENDING")),
                failed_stage=copy_item.get("failed_stage"),
            )
            items.append(copy_item)
        return items


def record_uploaded_document(
    *,
    filename: str,
    category: str,
    file_format: str,
    size_bytes: int,
    chunks_indexed: int,
    last_task_id: str,
    execution_mode: str,
    uploader: str,
    status: str = "INDEXED",
) -> Dict[str, Any]:
    """Persists metadata for an admin-uploaded knowledge document."""
    entry = {
        "filename": filename,
        "category": category,
        "format": file_format,
        "size_bytes": size_bytes,
        "chunks_indexed": chunks_indexed,
        "last_task_id": last_task_id,
        "execution_mode": execution_mode,
        "uploader": uploader,
        "status": status,
        "updated_at": _utc_now_iso(),
    }
    with _ledger_lock:
        _ensure_loaded_locked()
        _ledger_cache["documents"][filename] = entry
        _persist_locked()
    return dict(entry)


def get_uploaded_documents_map() -> Dict[str, Dict[str, Any]]:
    """Returns a shallow copy map of recorded uploaded document metadata keyed by filename."""
    with _ledger_lock:
        _ensure_loaded_locked()
        return {k: dict(v) for k, v in _ledger_cache["documents"].items()}
