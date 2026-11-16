from app.config import Settings
from app.queue.redis_client import RedisQueueClient


def clear_queue():
    settings = Settings()
    client = RedisQueueClient(
        redis_url=settings.redis_url,
        queue_name=settings.redis_queue_name,
    )

    print(f"Purging Redis queue: {client.queue_name}")
    try:
        client.purge_queue()
        print("Queue purged successfully.")
        return True
    except Exception as e:
        print(f"Error purging queue: {e}")
        return False


if __name__ == "__main__":
    clear_queue()
