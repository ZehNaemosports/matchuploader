from app.data.schema import Match
from app.downloader import YoutubeDownloader
from app.data.data import Data
from app.s3_client import S3client

class MatchDownloader:
    def __init__(self, youtube_downloader: YoutubeDownloader, data: Data, s3_client: S3client):
        self.s3_client = s3_client
        self.youtube_downloader = youtube_downloader
        self.data = data

    async def download_match_video(self, match_id: str):
        match: Match = await self.data.get_match(match_id)
        video_url = match.match_video
        print(video_url)
        video = await self.youtube_downloader.download(video_url)
        return video
    
    async def upload_match_video(self, file_path: str, object_key: str):
        return await self.s3_client.upload_file(file_path, object_key)
        
# curl -X GET "http://localhost:8000/api/matches/660e047d4e080294e44d5f3a/download"