import hashlib
import json

from app.cache.redis_client import get_redis_client
from app.config import CACHE_TTL_SECONDS


def build_cache_key(
    question: str,
    owner_id: int,
    document_name: str | None = None,
) -> str:
    normalized_question = question.strip().lower()
    normalized_document = (document_name or "__ALL__").strip().lower()
    cache_input = f"{owner_id}::{normalized_question}::{normalized_document}"
    cache_hash = hashlib.md5(cache_input.encode("utf-8")).hexdigest()
    return f"qa_cache:{cache_hash}"


def get_cached_answer(
    question: str,
    owner_id: int,
    document_name: str | None = None,
) -> dict | None:
    try:
        client = get_redis_client()
        cache_key = build_cache_key(question, owner_id, document_name)
        cached_value = client.get(cache_key)
        if not cached_value:
            return None
        return json.loads(cached_value)
    except Exception:
        return None


def set_cached_answer(
    question: str,
    answer: dict,
    owner_id: int,
    document_name: str | None = None,
) -> None:
    try:
        client = get_redis_client()
        cache_key = build_cache_key(question, owner_id, document_name)
        serialized = json.dumps(answer, ensure_ascii=False)
        client.setex(cache_key, CACHE_TTL_SECONDS, serialized)
    except Exception:
        pass


def clear_qa_cache() -> dict:
    try:
        client = get_redis_client()
        keys = list(client.scan_iter(match="qa_cache:*"))
        if not keys:
            return {"deleted_count": 0}
        deleted_count = client.delete(*keys)
        return {"deleted_count": int(deleted_count)}
    except Exception as exc:
        raise RuntimeError(f"clear qa cache failed: {exc}") from exc
