import json
import uuid

from app.cache.redis_client import get_redis_client
from app.config import TASK_STATUS_TTL_SECONDS


def create_task_id() -> str:
    """Generate a unique background task id."""
    return str(uuid.uuid4())


def build_task_key(task_id: str) -> str:
    """Build the Redis key used to store task status."""
    return f"task_status:{task_id}"


def create_task_record(task_id: str, task_type: str) -> None:
    """Create the initial pending task record in Redis."""
    client = get_redis_client()
    task_key = build_task_key(task_id)
    task_data = {
        "task_id": task_id,
        "task_type": task_type,
        "status": "pending",
        "message": "任务已创建，等待执行",
    }
    client.setex(
        task_key,
        TASK_STATUS_TTL_SECONDS,
        json.dumps(task_data, ensure_ascii=False),
    )


def update_task_status(task_id: str, status: str, message: str) -> None:
    """
    Update only status and message while preserving the original task_type.

    If the old task record is missing, create a minimal fallback record.
    """
    client = get_redis_client()
    task_key = build_task_key(task_id)
    old_value = client.get(task_key)

    if old_value:
        task_data = json.loads(old_value)
    else:
        task_data = {
            "task_id": task_id,
            "task_type": "unknown",
        }

    task_data["status"] = status
    task_data["message"] = message

    client.setex(
        task_key,
        TASK_STATUS_TTL_SECONDS,
        json.dumps(task_data, ensure_ascii=False),
    )


def get_task_status(task_id: str) -> dict | None:
    """Fetch the current task record from Redis."""
    client = get_redis_client()
    task_key = build_task_key(task_id)
    value = client.get(task_key)

    if not value:
        return None

    return json.loads(value)
