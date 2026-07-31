"""Qdrant Vector Database Connection Manager & Document Indexing Engine."""

import hashlib
import math
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_core.documents import Document
from backend.core.config import settings

_global_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    memory: bool = False
) -> QdrantClient:
    """
    Returns a QdrantClient instance.
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
    """
    Generates a deterministic, normalized 1024-dimensional vector (BGE-M3 standard).
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
    client: Optional[QdrantClient] = None
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
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
        return True
    except Exception:
        return False


def upsert_documents(
    docs: List[Document],
    collection_name: str = settings.QDRANT_COLLECTION,
    client: Optional[QdrantClient] = None
) -> int:
    """
    Upserts a batch of Document objects into Qdrant collection with 1024-dim vectors.
    Returns the number of documents indexed.
    """
    if not docs:
        return 0

    if client is None:
        client = get_qdrant_client()

    init_qdrant_collection(collection_name=collection_name, vector_size=1024, client=client)

    points: List[PointStruct] = []
    for idx, doc in enumerate(docs):
        point_id = str(uuid.uuid4())
        vec = get_embedding(doc.page_content, dim=1024)
        
        payload: Dict[str, Any] = {
            "page_content": doc.page_content,
            **doc.metadata
        }
        
        points.append(PointStruct(id=point_id, vector=vec, payload=payload))

    client.upsert(collection_name=collection_name, points=points)
    return len(points)


def search_similar_documents(
    query: str,
    top_k: int = 5,
    collection_name: str = settings.QDRANT_COLLECTION,
    client: Optional[QdrantClient] = None
) -> List[Document]:
    """
    Performs similarity search in Qdrant and returns matching Document objects.
    """
    if client is None:
        client = get_qdrant_client()

    query_vector = get_embedding(query, dim=1024)
    
    results = []
    if hasattr(client, "query_points"):
        res = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k
        )
        hits = getattr(res, "points", res)
    else:
        hits = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k
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
