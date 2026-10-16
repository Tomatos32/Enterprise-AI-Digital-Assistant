"""Qdrant Vector Database Connection Manager & RBAC Security Filter Engine."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from langchain_core.documents import Document
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from backend.core.config import settings
from backend.rag.embeddings import (
    get_embedding,
    get_embeddings_batch,
    get_embedding_engine_info,
)

logger = logging.getLogger(__name__)

_global_qdrant_client: Optional[QdrantClient] = None
_global_qdrant_mode: str = "uninitialized"


class DocumentSecurity(BaseModel):
    """Document-level Security Metadata Model for RBAC and Multi-tenancy."""

    tenant_id: str = Field("default", description="Tenant Identifier")
    allowed_departments: List[str] = Field(
        default_factory=lambda: ["ALL"],
        description="List of departments permitted to access (e.g. ['研发部', 'ALL'])",
    )
    security_clearance_level: int = Field(
        1,
        description="Minimum security clearance level (1=Public, 2=Internal, 3=Confidential, 4=TopSecret)",
    )


def build_rbac_filter(
    tenant_id: str = "default",
    user_department: Optional[str] = None,
    clearance_level: int = 1,
) -> Filter:
    """Constructs a physical Qdrant Filter enforcing Multi-tenancy and RBAC isolation.

    Rules:
    1. tenant_id must match strictly.
    2. allowed_departments must contain either user_department or 'ALL'.
    3. security_clearance_level must be <= user clearance_level.
    """
    allowed_depts = ["ALL"]
    if user_department:
        allowed_depts.append(user_department)

    must_conditions = [
        FieldCondition(
            key="tenant_id",
            match=MatchValue(value=tenant_id),
        ),
        FieldCondition(
            key="allowed_departments",
            match=MatchAny(any=allowed_depts),
        ),
        FieldCondition(
            key="security_clearance_level",
            range=Range(lte=clearance_level),
        ),
    ]

    return Filter(must=must_conditions)


def reset_qdrant_client():
    """Resets the global Qdrant client singleton (useful for testing)."""
    global _global_qdrant_client, _global_qdrant_mode
    if _global_qdrant_client is not None:
        try:
            _global_qdrant_client.close()
        except Exception:
            pass
    _global_qdrant_client = None
    _global_qdrant_mode = "uninitialized"


def get_qdrant_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    memory: bool = False,
    storage_path: Optional[str] = None,
) -> QdrantClient:
    """Returns a QdrantClient instance.

    Priority:
    1. If `memory=True` or `host == ':memory:'`: In-memory isolated client.
    2. If explicit host/port passed: Connect to specified remote server.
    3. Global singleton:
       a. Attempt remote connection to settings.QDRANT_HOST:settings.QDRANT_PORT.
       b. Fallback to local persistent disk storage (settings.QDRANT_STORAGE_PATH).
       c. Fallback to in-memory if local disk initialization fails.
    """
    global _global_qdrant_client, _global_qdrant_mode

    if memory or host == ":memory:":
        return QdrantClient(":memory:")

    if host or port:
        return QdrantClient(host=host or settings.QDRANT_HOST, port=port or settings.QDRANT_PORT, timeout=1.5)

    if _global_qdrant_client is not None:
        underlying = getattr(_global_qdrant_client, "_client", None)
        if underlying is not None and getattr(underlying, "closed", False):
            _global_qdrant_client = None
            _global_qdrant_mode = "uninitialized"
        else:
            return _global_qdrant_client

    # 1. Try remote server
    try:
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=1.0)
        client.get_collections()
        _global_qdrant_client = client
        _global_qdrant_mode = "remote_server"
        logger.info("Connected to remote Qdrant server at %s:%s", settings.QDRANT_HOST, settings.QDRANT_PORT)
        return _global_qdrant_client
    except Exception:
        pass

    # 2. Try local disk persistence
    try:
        path_to_use = storage_path or settings.QDRANT_STORAGE_PATH
        storage_dir = Path(path_to_use)
        storage_dir.mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=str(storage_dir))
        _global_qdrant_client = client
        _global_qdrant_mode = "local_storage"
        logger.info("Initialized local persistent Qdrant storage at %s", storage_dir)
        return _global_qdrant_client
    except Exception as exc:
        logger.warning("Failed to initialize local persistent Qdrant at %s: %s. Falling back to :memory:", path_to_use, exc)

    # 3. Final fallback: in-memory
    _global_qdrant_client = QdrantClient(":memory:")
    _global_qdrant_mode = "in_memory"
    return _global_qdrant_client


def get_qdrant_info(client: Optional[QdrantClient] = None) -> Dict[str, Any]:
    """Returns comprehensive diagnostic telemetry for the Qdrant vector database."""
    global _global_qdrant_mode

    if client is None:
        client = get_qdrant_client()

    mode = _global_qdrant_mode if client == _global_qdrant_client else "custom_instance"
    storage_loc = settings.QDRANT_STORAGE_PATH if mode == "local_storage" else f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"

    try:
        col_res = client.get_collections()
        col_names = [c.name for c in col_res.collections]
        target_col = settings.QDRANT_COLLECTION

        points_count = 0
        vector_size = settings.EMBEDDING_DIMENSION

        if target_col in col_names:
            try:
                cnt_res = client.count(collection_name=target_col)
                points_count = cnt_res.count
            except Exception:
                points_count = 0

            try:
                col_info = client.get_collection(collection_name=target_col)
                if hasattr(col_info.config.params, "vectors"):
                    vectors_cfg = col_info.config.params.vectors
                    if hasattr(vectors_cfg, "size"):
                        vector_size = vectors_cfg.size
            except Exception:
                pass

        return {
            "status": "healthy",
            "client_mode": mode,
            "storage_location": storage_loc,
            "all_collections": col_names,
            "collection_name": target_col,
            "collection_exists": target_col in col_names,
            "points_count": points_count,
            "vector_size": vector_size,
            "embedding_engine": get_embedding_engine_info(),
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "client_mode": mode,
            "storage_location": storage_loc,
            "error": str(exc),
            "collection_name": settings.QDRANT_COLLECTION,
            "collection_exists": False,
            "points_count": 0,
            "vector_size": settings.EMBEDDING_DIMENSION,
            "embedding_engine": get_embedding_engine_info(),
        }


def init_qdrant_collection(
    collection_name: str = settings.QDRANT_COLLECTION,
    vector_size: int = 1024,
    client: Optional[QdrantClient] = None,
) -> bool:
    """Ensures Qdrant collection exists with Cosine similarity configuration."""
    if client is None:
        client = get_qdrant_client()

    try:
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if collection_name not in collection_names:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        return True
    except Exception:
        return False


def upsert_documents(
    docs: List[Document],
    collection_name: str = settings.QDRANT_COLLECTION,
    client: Optional[QdrantClient] = None,
    default_security: Optional[DocumentSecurity] = None,
) -> int:
    """Upserts a batch of Document objects into Qdrant collection with embeddings

    and enforces RBAC security metadata.
    """
    if not docs:
        return 0

    if client is None:
        client = get_qdrant_client()

    dim = settings.EMBEDDING_DIMENSION
    init_qdrant_collection(collection_name=collection_name, vector_size=dim, client=client)

    sec = default_security or DocumentSecurity()
    texts = [d.page_content for d in docs]
    vectors = get_embeddings_batch(texts, dim=dim)

    points: List[PointStruct] = []
    for doc, vec in zip(docs, vectors):
        point_id = str(uuid.uuid4())
        meta = dict(doc.metadata) if doc.metadata else {}

        # Ensure security fields are present
        if "tenant_id" not in meta:
            meta["tenant_id"] = sec.tenant_id
        if "allowed_departments" not in meta:
            meta["allowed_departments"] = sec.allowed_departments
        if "security_clearance_level" not in meta:
            meta["security_clearance_level"] = sec.security_clearance_level

        payload: Dict[str, Any] = {
            "page_content": doc.page_content,
            **meta,
        }

        points.append(PointStruct(id=point_id, vector=vec, payload=payload))

    client.upsert(collection_name=collection_name, points=points)
    return len(points)


def search_similar_documents(
    query: str,
    top_k: int = 5,
    collection_name: str = settings.QDRANT_COLLECTION,
    client: Optional[QdrantClient] = None,
    query_filter: Optional[Filter] = None,
    tenant_id: Optional[str] = None,
    user_department: Optional[str] = None,
    clearance_level: Optional[int] = None,
) -> List[Document]:
    """Performs similarity search in Qdrant with optional RBAC payload filtering."""
    if client is None:
        client = get_qdrant_client()

    dim = settings.EMBEDDING_DIMENSION
    query_vector = get_embedding(query, dim=dim)

    # Resolve filter
    effective_filter = query_filter
    if effective_filter is None and (tenant_id or user_department or clearance_level is not None):
        effective_filter = build_rbac_filter(
            tenant_id=tenant_id or "default",
            user_department=user_department,
            clearance_level=clearance_level if clearance_level is not None else 1,
        )

    results = []
    if hasattr(client, "query_points"):
        res = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=effective_filter,
            limit=top_k,
        )
        hits = getattr(res, "points", res)
    else:
        hits = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=effective_filter,
            limit=top_k,
        )

    for hit in hits:
        payload = hit.payload or {}
        content = payload.get("page_content", "")
        meta = {k: v for k, v in payload.items() if k != "page_content"}
        meta["score"] = getattr(hit, "score", 0.0)
        results.append(Document(page_content=content, metadata=meta))

    return results


def check_qdrant_health(client: Optional[QdrantClient] = None) -> bool:
    """Checks Qdrant connectivity."""
    try:
        if client is None:
            client = get_qdrant_client()
        client.get_collections()
        return True
    except Exception:
        return False
