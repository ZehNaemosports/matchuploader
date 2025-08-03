from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.data.data import Data
from app.downloader import YoutubeDownloader
from app.s3_client import S3client
from app.service.matchdownloader import MatchDownloader

def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.mongodb

async def get_s3_client(request: Request) -> S3client:
    return request.app.state.s3_client

async def get_data(database: AsyncIOMotorDatabase = Depends(get_db)) -> Data:
    return Data(database=database)

async def get_youtube_downloader(request: Request) -> YoutubeDownloader:
    return request.app.state.youtube_downloader

async def get_match_downloader(
    data: Data = Depends(get_data),
    s3_client: S3client = Depends(get_s3_client),
    youtube_downloader: YoutubeDownloader = Depends(get_youtube_downloader)
) -> MatchDownloader:
    return MatchDownloader(
        youtube_downloader=youtube_downloader,
        data=data,
        s3_client=s3_client
    )