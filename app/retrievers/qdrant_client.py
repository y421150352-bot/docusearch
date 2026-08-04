from functools import lru_cache

from qdrant_client import QdrantClient

from app.config import QDRANT_API_KEY, QDRANT_TIMEOUT, QDRANT_URL


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY or None,
        timeout=QDRANT_TIMEOUT,
        trust_env=False,
    )
