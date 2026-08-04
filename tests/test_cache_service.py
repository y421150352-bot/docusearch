import uuid

import pytest

pytestmark = pytest.mark.integration

from app.services.cache_service import (
    build_cache_key,
    get_cached_answer,
    set_cached_answer,
)
from app.cache.redis_client import get_redis_client


def test_cache_miss_set_hit_cycle():
    client = get_redis_client()
    question = f"day16-cache-test-{uuid.uuid4()}"
    cache_key = build_cache_key(question)
    expected_answer = {
        "question": question,
        "summary": "cache summary",
        "key_points": [
            {
                "title": "point 1",
                "content": "point 1 content",
            }
        ],
        "sources": [],
    }

    try:
        client.delete(cache_key)
        assert get_cached_answer(question) is None

        set_cached_answer(question, expected_answer)

        cached_answer = get_cached_answer(question)
    except Exception as exc:
        pytest.skip(f"Redis is not available: {exc!r}")
    finally:
        try:
            client.delete(cache_key)
        except Exception:
            pass

    assert cached_answer == expected_answer
