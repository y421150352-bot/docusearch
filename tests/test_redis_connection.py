import pytest

pytestmark = pytest.mark.integration

from app.cache.redis_client import get_redis_client


def test_redis_ping():
    client = get_redis_client()

    try:
        result = client.ping()
    except Exception as exc:
        pytest.skip(f"Redis is not available: {exc!r}")

    assert result is True
