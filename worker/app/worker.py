import os
import time

from redis import Redis
from rq import Worker

from app.config import settings
from app import tasks  # noqa: F401 — register job handlers for RQ


def main() -> None:
    redis_url = settings.redis_url
    conn = Redis.from_url(redis_url)
    os.environ.setdefault("RQ_SETTINGS", "")
    w = Worker(["medimage"], connection=conn, name=f"worker-{os.getpid()}")
    while True:
        w.work(with_scheduler=False, logging_level="INFO")
        time.sleep(1)


if __name__ == "__main__":
    main()
