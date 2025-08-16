import subprocess
from pathlib import Path
from typing import Optional
import time
import os
import logging

logger = logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
class YoutubeDownloader:
    def __init__(self, quality='720', cookies_path: Optional[str] = "/home/ubuntu/cookies.txt", use_tor=True):
        self.quality = quality
        self.cookies_path = cookies_path
        self.use_tor = use_tor

    def set_quality(self, quality):
        self.quality = quality

    def _ensure_tor_running(self):
        try:
            # Check if Tor is active
            subprocess.run(["systemctl", "is-active", "--quiet", "tor"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Start Tor if not running
            subprocess.run(["sudo", "service", "tor", "start"], check=True)
            # Wait for Tor to initialize
            time.sleep(5)

    def _build_base_command(self):
        """Build common command arguments with Tor support if enabled"""
        cmd = ['yt-dlp']
        
        if self.use_tor:
            self._ensure_tor_running()
            cmd.extend([
                '--proxy', 'socks5://localhost:9050',
                '--socket-timeout', '60',
                '--retries', '10',
                '--force-ipv4'
            ])
        
        if self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(['--cookies', self.cookies_path])
            
        return cmd

    async def download(self, url: str, filename: str) -> Optional[str]:
        base_cmd = self._build_base_command()
        output_path = f"{filename}.mp4"
        
        if "app.veo.co" in url:
            try:
                veo_cmd = base_cmd + [
                    "-f", "standard-1080p",
                    "-o", output_path,
                    "--merge-output-format", "mp4",
                    "--no-check-certificate",
                    url
                ]
                
                result = subprocess.run(veo_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    return Path(output_path).absolute()
                logger.info("Veo download failed:", result.stderr)
                return None
                
            except Exception as e:
                logger.info(f"Error downloading Veo video: {str(e)}")
                return None
            
        format_selector = f'bestvideo[height<={self.quality}]+bestaudio/best[height<={self.quality}]'
        
        yt_cmd = base_cmd + [
            '-f', format_selector,
            '--merge-output-format', 'mp4',
            '--embed-thumbnail',
            '--embed-metadata',
            '--audio-quality', '0',
            '-o', output_path,
            '--no-simulate',
            url
        ]

        try:
            logger.info(f"Downloading video from {url}")
            result = subprocess.run(yt_cmd, capture_output=True, text=True)
            if Path(output_path).exists():
                logger.info("download done")
                return Path(output_path).absolute()
                
            logger.info("YouTube download failed. Possible solutions:")
            logger.info("1. Try different quality (currently set to {self.quality})")
            logger.info("Error details:", result.stderr)
            return None

        except Exception as e:
            logger.info(f"Critical error: {str(e)}")
            return None
        
# s = YoutubeDownloader()
# print(s.download(url="https://app.veo.co/matches/20250727-ivory-coast-contre-makinde-fc-vs-kolia-fc-ligafci-a2d2c313/", filename="test"))