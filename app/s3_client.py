import boto3
from botocore.exceptions import ClientError
from starlette.concurrency import run_in_threadpool

class S3client:
    def __init__(self, aws_access_key, aws_secret_key, aws_region, aws_bucket, logger):
        self.logger = logger
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region
        self.aws_bucket = aws_bucket
        self.client = boto3.client('s3', aws_access_key_id=self.aws_access_key, aws_secret_access_key=self.aws_secret_key, region_name=self.aws_region)

    async def upload_file(self, file_path: str, object_key: str):
        try:
            await run_in_threadpool(
                self.client.upload_file,
                Filename=file_path,
                Bucket=self.aws_bucket,
                Key=object_key,
            )
            return True
        except Exception as e:
            self.logger.error(f"Error uploading file: {e}", exc_info=True)
            return False
        
    async def download_file(self, object_key: str, file_path: str):
        try:
            await run_in_threadpool(
                self.client.download_file,
                Bucket=self.aws_bucket,
                Key=object_key,
                Filename=file_path,
            )
            return True
        except Exception as e:
            self.logger.error(f"Error downloading file: {e}", exc_info=True)
            return False
        
    async def check_file_exists(self, object_key: str):
        try:
            await run_in_threadpool(self.client.head_object, Bucket=self.aws_bucket, Key=object_key)
            self.logger.info(f"File '{object_key}' found in bucket '{self.aws_bucket}'.")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                self.logger.info(f"File '{object_key}' does not exist in bucket '{self.aws_bucket}'.")
                return False
            self.logger.error(f"AWS ClientError checking if file exists: {e}", exc_info=True)
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred checking if file exists: {e}", exc_info=True)
            return False