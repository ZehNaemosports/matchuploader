from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.data.data import Data
from app.downloader import YoutubeDownloader
from app.queue.sqs_client import SqsClient
from app.s3_client import S3client
from app.service.matchdownloader import MatchDownloader

def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.mongodb

async def get_s3_client(request: Request) -> S3client:
    return request.app.state.s3_client

async def get_data(request: Request) -> Data:
    return request.app.state.data

async def get_youtube_downloader(request: Request) -> YoutubeDownloader:
    return request.app.state.youtube_downloader

async def get_sqs_client(request: Request) -> SqsClient:
    return request.app.state.sqs_client

async def get_match_downloader(request: Request) -> MatchDownloader:
    return request.app.state.match_downloader