import os
from dotenv import load_dotenv
from app.queue.sqs_client import SqsClient

# Load environment variables from .env file
load_dotenv()

def clear_queue():
    print("Connecting to SQS queue...")
    client = SqsClient(
        aws_access_key=os.environ.get("AWS_ACCESS_KEY", ""),
        aws_secret_key=os.environ.get("AWS_SECRET_KEY", ""),
        aws_region=os.environ.get("AWS_REGION", ""),
        aws_queue_url=os.environ.get("SQS_QUEUE_URL", "")
    )
    
    sqs = client.get_client()
    queue_url = client.queue_url
    
    print(f"Purging queue: {queue_url}")
    try:
        response = sqs.purge_queue(QueueUrl=queue_url)
        print("Queue purged successfully.")
        return True
    except Exception as e:
        print(f"Error purging queue: {e}")
        return False

if __name__ == "__main__":
    clear_queue()
