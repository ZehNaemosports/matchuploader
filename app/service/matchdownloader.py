from app.data.schema import Match
from app.downloader import YoutubeDownloader
from app.data.data import Data
from app.s3_client import S3client
import re

class MatchDownloader:
    def __init__(self, youtube_downloader: YoutubeDownloader, data: Data, s3_client: S3client):
        self.s3_client = s3_client
        self.youtube_downloader = youtube_downloader
        self.data = data

    async def download_match_video(self, match_id: str):
        match: Match = await self.data.get_match(match_id)
        if not match:
            print(f"No match found for {match_id}")
            return None

        date_str = match.date or "unknown-date"
        home_team = match.home_team_string or "HomeTeam"
        away_team = match.away_team_string or "AwayTeam"
        video_url = match.match_video

        if not video_url:
            print(f"No video URL for match {match_id}")
            return None

        try:
            date_only = date_str.split("T")[0].replace("/", "-")
        except Exception:
            date_only = "unknown-date"

        home_clean = re.sub(r'[^A-Za-z0-9]', '', home_team)
        away_clean = re.sub(r'[^A-Za-z0-9]', '', away_team)

        filename = f"{home_clean}V{away_clean}-{date_only}"
        print(f"Downloading video for match {match_id} as {filename}")

        try:
            video = await self.youtube_downloader.download(url=video_url, filename=filename)
            return video
        except Exception as e:
            print(f"Failed to download video for match {match_id}: {e}")
            return None
    
    async def upload_match_video(self, file_path: str, object_key: str):
        return await self.s3_client.upload_file(file_path, object_key)
        
# curl -X GET "http://localhost:8000/api/matches/660e047d4e080294e44d5f3a/download"