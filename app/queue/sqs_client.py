import boto3


class SqsClient:
    def __init__(self, aws_access_key, aws_secret_key, aws_region, aws_queue_url):
        self.access_key = aws_access_key
        self.secret_key = aws_secret_key
        self.region = aws_region
        self.queue_url = aws_queue_url
        self.client = None

    def connect(self):
        if not self.client:
            self.client = boto3.client(
                'sqs',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
        return self.client

    def get_client(self):
        return self.connect()

    def send_message(self, message):
        client = self.get_client()
        response = client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=message
        )
        return response
    
    def delete_message(self, receipt_handle):
        client = self.get_client()
        response = client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle
        )
        return response
    
    def receive_message(self):
        client = self.get_client()
        response = client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=900
        )
        return response
