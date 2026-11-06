import redis
from rq import Queue

from app.config import settings


def get_queue(name: str = "medimage") -> Queue:
    conn = redis.from_url(settings.redis_url)
    return Queue(name, connection=conn)
