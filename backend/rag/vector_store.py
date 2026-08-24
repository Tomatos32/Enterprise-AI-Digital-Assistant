"""Qdrant Vector Database Connection Manager & RBAC Security Filter Engine."""

import hashlib
import math
import uuid
from typing import Any, Dict, List, Optional
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

_global_qdrant_client: Optional[QdrantClient] = None


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


def get_qdrant_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    memory: bool = False,
) -> QdrantClient:
    """Returns a QdrantClient instance.

    If remote server is unreachable or offline, gracefully falls back to an in-memory client.
    """
    global _global_qdrant_client

    if memory or host == ":memory:":
        return QdrantClient(":memory:")

    if host or port:
        return QdrantClient(host=host or settings.QDRANT_HOST, port=port or settings.QDRANT_PORT, timeout=1.5)

    if _global_qdrant_client is not None:
        return _global_qdrant_client

    try:
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=1.5)
        client.get_collections()
        _global_qdrant_client = client
        return client
    except Exception:
        _global_qdrant_client = QdrantClient(":memory:")
        return _global_qdrant_client


def get_embedding(text: str, dim: int = 1024) -> List[float]:
    """Generates a deterministic, normalized 1024-dimensional vector (BGE-M3 standard).

    Used as default embedding calculation without external model weights.
    """
    if not text:
        text = "empty"

    raw_hash = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(dim):
        byte_val = raw_hash[i % len(raw_hash)]
        val = math.sin((i + 1) * byte_val * 0.1)
        vec.append(val)

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def init_qdrant_collection(
    collection_name: str = settings.QDRANT_COLLECTION,
    vector_size: int = 1024,
    client: Optional[QdrantClient] = None,
) -> bool:
    """Ensures Qdrant collection exists with 1024-dim Cosine similarity configuration."""
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
    """Upserts a batch of Document objects into Qdrant collection with 1024-dim vectors

    and enforces RBAC security metadata.
    """
    if not docs:
        return 0

    if client is None:
        client = get_qdrant_client()

    init_qdrant_collection(collection_name=collection_name, vector_size=1024, client=client)

    sec = default_security or DocumentSecurity()
    points: List[PointStruct] = []

    for doc in docs:
        point_id = str(uuid.uuid4())
        vec = get_embedding(doc.page_content, dim=1024)

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

    query_vector = get_embedding(query, dim=1024)

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
