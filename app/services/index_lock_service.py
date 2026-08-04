from app.cache.redis_client import get_redis_client


REBUILD_INDEX_LOCK_KEY = "rebuild_index_lock"


def acquire_rebuild_index_lock(task_id: str, ttl_seconds: int = 600) -> bool:
    client = get_redis_client()
    return bool(
        client.set(
            REBUILD_INDEX_LOCK_KEY,
            task_id,
            nx=True,
            ex=ttl_seconds,
        )
    )


def release_rebuild_index_lock(task_id: str) -> bool:
    client = get_redis_client()
    current_value = client.get(REBUILD_INDEX_LOCK_KEY)
    if current_value != task_id:
        return False
    return bool(client.delete(REBUILD_INDEX_LOCK_KEY))
