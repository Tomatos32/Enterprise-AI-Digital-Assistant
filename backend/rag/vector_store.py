"""Qdrant Vector Database Connection Manager & Collection Factory."""

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from backend.core.config import settings


def get_qdrant_client() -> QdrantClient:
    """
    Returns QdrantClient instance.
    """
    return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


def init_qdrant_collection() -> bool:
    """
    Ensures default enterprise knowledge collection exists.
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if settings.QDRANT_COLLECTION not in collection_names:
            client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
            )
        return True
    except Exception:
        return False


def check_qdrant_health() -> bool:
    """
    Checks Qdrant connectivity.
    """
    try:
        client = get_qdrant_client()
        client.get_collections()
        return True
    except Exception:
        return False
