import logging
import os

from redis import Redis
from rq import Queue, Worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def main():
    connection = Redis.from_url(REDIS_URL)
    queue = Queue(connection=connection)
    logger.info("worker started")
    Worker([queue], connection=connection).work()


if __name__ == "__main__":
    main()
