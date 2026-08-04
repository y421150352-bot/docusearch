import redis

from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

#返回一个 Redis 客户端对象
def get_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD or None,
        decode_responses=True
    )
