import json
import uuid

import redis


class RedisQueueClient:
    def __init__(self, redis_url, queue_name="matchuploader"):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.processing_queue_name = f"{queue_name}:processing"
        self.client = None

    def connect(self):
        if not self.client:
            self.client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self.client

    def get_client(self):
        return self.connect()

    def send_message(self, message):
        message_id = str(uuid.uuid4())
        envelope = json.dumps({"id": message_id, "body": message})
        self.get_client().lpush(self.queue_name, envelope)
        return {"MessageId": message_id}

    def delete_message(self, receipt_handle):
        if receipt_handle:
            self.get_client().lrem(self.processing_queue_name, 1, receipt_handle)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def receive_message(self, wait_seconds=20):
        raw = self.get_client().brpoplpush(
            self.queue_name,
            self.processing_queue_name,
            timeout=wait_seconds,
        )

        if not raw:
            return {}

        try:
            envelope = json.loads(raw)
            body = envelope["body"]
            message_id = envelope["id"]
        except (ValueError, KeyError, TypeError):
            body = raw
            message_id = None

        return {
            "Messages": [
                {
                    "Body": body,
                    "ReceiptHandle": raw,
                    "MessageId": message_id,
                }
            ]
        }

    def purge_queue(self):
        self.get_client().delete(self.queue_name, self.processing_queue_name)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}
