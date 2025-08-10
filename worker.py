import asyncio
from app.queue.message_queue_processor import MessageProcessor
from app.s3_client import S3client
from app.data.data import Data
from app.downloader import YoutubeDownloader
from app.queue.sqs_client import SqsClient
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import Settings

async def main():
    settings = Settings()

    s3_client = S3client(
        aws_access_key=settings.aws_access_key,
        aws_secret_key=settings.aws_secret_key,
        aws_region=settings.aws_region,
        aws_bucket=settings.aws_bucket
    )

    sqs_client = SqsClient(
        aws_access_key=settings.aws_access_key,
        aws_region=settings.aws_region,
        aws_secret_key=settings.aws_secret_key,
        aws_queue_url=settings.sqs_queue_url
    )

    mongodb_client = AsyncIOMotorClient(settings.database_connection_string)
    mongodb = mongodb_client[settings.database_name]
    data_service = Data(database=mongodb)
    youtube_downloader = YoutubeDownloader()

    from app.service.matchdownloader import MatchDownloader
    match_downloader = MatchDownloader(
        youtube_downloader=youtube_downloader,
        data=data_service,
        s3_client=s3_client
    )

    processor = MessageProcessor(sqs_client=sqs_client, match_downloader=match_downloader)
    await processor.poll_messages()

if __name__ == "__main__":
    asyncio.run(main())
