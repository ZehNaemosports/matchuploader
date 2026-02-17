from app.data.schema import Match
from app.downloader import YoutubeDownloader
from app.data.data import Data
from app.s3_client import S3client
import re
import logging
from moviepy import VideoFileClip, concatenate_videoclips
import asyncio
import subprocess
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MatchDownloader:
    def __init__(self, youtube_downloader: YoutubeDownloader, data: Data, s3_client: S3client):
        self.s3_client = s3_client
        self.youtube_downloader = youtube_downloader
        self.data = data

    async def download_match_video(self, match_id: str):
        match: Match = await self.data.get_match(match_id)
        if not match:
            logger.info(f"No match found for {match_id}")
            return None

        date_str = match.date or "unknown-date"
        home_team = match.home_team_string or "HomeTeam"
        away_team = match.away_team_string or "AwayTeam"
        video_url = match.match_video

        if not video_url:
            logger.info(f"No video URL for match {match_id}")
            return None

        try:
            date_only = date_str.split("T")[0].replace("/", "-")
        except Exception:
            date_only = "unknown-date"

        home_clean = re.sub(r'[^A-Za-z0-9]', '', home_team)
        away_clean = re.sub(r'[^A-Za-z0-9]', '', away_team)

        filename = f"{home_clean}V{away_clean}-{date_only}"
        logger.info(f"Downloading video for match {match_id} as {filename}")

        try:
            video = await self.youtube_downloader.download(url=video_url, filename=filename)
            return video
        except Exception as e:
            logger.info(f"Failed to download video for match {match_id}: {e}")
            return None
    
    async def upload_match_video(self, file_path: str, object_key: str):
        return await self.s3_client.upload_file(file_path, object_key)

    async def merge_videos(self, video1: str, video2: str, output_name: str = None):
        video1_path = await self.youtube_downloader.download(video1, filename="vid1")
        video2_path = await self.youtube_downloader.download(video2, filename="vid2")
        
        if output_name is None:
            output_name = "merged_video.mp4"

        list_path = "inputs.txt"
        with open(list_path, "w") as f:
            f.write(f"file '{os.path.abspath(video1_path)}'\n")
            f.write(f"file '{os.path.abspath(video2_path)}'\n")

        try:
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
                "-i", list_path, "-c", "copy", output_name
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

        except Exception as e:
            
            clip1 = VideoFileClip(video1_path)
            clip2 = VideoFileClip(video2_path)
            final_clip = concatenate_videoclips([clip1, clip2])
            
            final_clip.write_videofile(
                output_name, 
                codec="libx264", 
                audio_codec="aac", 
                threads=8, 
                preset="ultrafast", 
                ffmpeg_params=["-crf", "17"]
            )
            clip1.close()
            clip2.close()
            final_clip.close()
        
        finally:
            if os.path.exists(list_path):
                os.remove(list_path)

        return output_name, video2_path, video1_path

        
# curl -X GET "http://localhost:8000/api/matches/660e047d4e080294e44d5f3a/download"