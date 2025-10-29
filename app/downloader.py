import subprocess
from pathlib import Path
from typing import Optional
import time
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
            subprocess.run(["systemctl", "is-active", "--quiet", "tor"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Start Tor if not running
            subprocess.run(["sudo", "service", "tor", "start"], check=True)
            # Wait for Tor to initialize
            time.sleep(3)
            logger.info("Tor service started")

    def _build_base_command(self):
        """Build common command arguments with Tor support if enabled"""
        cmd = ['yt-dlp', '--no-playlist']
        
        if self.use_tor:
            # self._ensure_tor_running()
            cmd.extend([
                '--proxy', 'socks5://localhost:9050',
                '--socket-timeout', '60',
                '--retries', '10',
                '--force-ipv4',
                # '--extractor-args', 'youtube:player_client=android',
                # '--throttled-rate', '100K'
            ])
            
        if not self.use_tor and self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(['--cookies', self.cookies_path])
            
        return cmd

    async def list_formats(self, url: str):
        """List available formats for a YouTube video"""
        try:
            base_cmd = self._build_base_command()
            list_cmd = base_cmd + ['--list-formats', url]
            
            logger.info(f"Listing available formats for: {url}")
            logger.info(f"Command: {' '.join(list_cmd)}")
            
            result = subprocess.run(list_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Available formats:\n{result.stdout}")
                return result.stdout
            else:
                logger.error(f"Failed to list formats: {result.stderr}")
                return None
                
        except Exception as e:
            logger.exception(f"Error listing formats: {str(e)}")
            return None

    async def download(self, url: str, filename: str) -> Optional[str]:
        try:
            formats_info = await self.list_formats(url)
            if not formats_info:
                logger.warning("Could not retrieve format information")
            
            base_cmd = self._build_base_command()
            output_path = f"{filename}.mp4"
            
            if "app.veo.co" in url:
                # Veo downloads
                veo_cmd = base_cmd + [
                    "-f", "standard-1080p",
                    "-o", output_path,
                    "--merge-output-format", "mp4",
                    "--no-check-certificate",
                    url
                ]
                
                if '--cookies' in veo_cmd:
                    idx = veo_cmd.index('--cookies')
                    del veo_cmd[idx:idx+2]
                
                logger.info(f"Downloading Veo video with command: {' '.join(veo_cmd)}")
                result = subprocess.run(veo_cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and Path(output_path).exists():
                    logger.info(f"Veo download completed successfully: {output_path}")
                    return str(Path(output_path).absolute())
                
                logger.error(f"Veo download failed: {result.stderr}")
                return None
            
            format_selector = f'bestvideo[height<=720]+bestaudio'
            
            yt_cmd = base_cmd + [
                '-f', format_selector,
                '--remux-video', 'mp4',
                '--embed-thumbnail',
                '--embed-metadata',
                '--audio-quality', '0',
                '--progress',
                '--no-part',
                '-o', output_path,
                url
            ]
            
            logger.info(f"Downloading YouTube video: {url}")
            logger.info(f"Output path: {output_path}")
            logger.info(f"Using format selector: {format_selector}")
            
            result = subprocess.run(yt_cmd, capture_output=True, text=True)
            
            if Path(output_path).exists():
                file_size = os.path.getsize(output_path) / (1024 * 1024) 
                logger.info(f"YouTube download completed: {output_path} ({file_size:.2f} MB)")
                return str(Path(output_path).absolute())
                
            logger.error("Error downloading video")
            logger.error(f"Error details: {result.stderr}")
            
            return None

        except Exception as e:
            logger.exception(f"Critical error in download: {str(e)}")
            return None
