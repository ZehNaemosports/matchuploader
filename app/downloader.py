import subprocess
import json
from pathlib import Path
from typing import Optional

class YoutubeDownloader:
    def __init__(self, quality='720'):
        self.quality = quality

    def set_quality(self, quality):
        self.quality = quality

    async def download(self, url) -> Optional[Path]:
        """Downloads a YouTube video and returns the path to the downloaded file"""
        format_selector = f'bestvideo[height<={self.quality}]+bestaudio/best[height<={self.quality}]'
        
        cmd = [
            'yt-dlp',
            '-f', format_selector,
            '--merge-output-format', 'mp4',
            '--embed-thumbnail',
            '--embed-metadata',
            '--audio-quality', '0',
            '--print-json',
            '-o', '%(title)s.%(ext)s',
            '--no-simulate',
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            info = json.loads(result.stdout)
            filename = info.get('_filename')
            
            if filename:
                return Path(filename).absolute()
            return None
            
        except subprocess.CalledProcessError as e:
            print("Download failed:", e)
            return None
        except FileNotFoundError:
            print("Error: yt-dlp not found. Please install yt-dlp first.")
            return None
        except json.JSONDecodeError:
            print("Error parsing yt-dlp output")
            return None

# Tests
# downloader = YoutubeDownloader(quality='720')
# print(downloader.download("https://youtu.be/n-smKoW2XdM"))