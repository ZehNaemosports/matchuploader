import subprocess
from pathlib import Path
from typing import Optional
import time
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YoutubeDownloader:
    def __init__(self, quality='720', cookies_path: Optional[str] = "/home/ubuntu/cookies.txt", use_tor=Tor):
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
            
            output_path = f"{filename}.mp4"
            
            # Check for Veo videos first
            if "app.veo.co" in url or "veo" in url.lower():
                # Veo downloads
                veo_cmd = [
                    'yt-dlp',
                    "-f", "standard-1080p",
                    "-o", output_path,
                    "--merge-output-format", "mp4",
                    "--no-check-certificate",
                    "--no-playlist",
                    url
                ]
                
                logger.info(f"Downloading Veo video with command: {' '.join(veo_cmd)}")
                result = subprocess.run(veo_cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and Path(output_path).exists():
                    file_size = os.path.getsize(output_path) / (1024 * 1024)
                    logger.info(f"Veo download completed successfully: {output_path} ({file_size:.2f} MB)")
                    return str(Path(output_path).absolute())
                
                logger.error(f"Veo download failed: {result.stderr}")
                return None
            
            # Use the exact command that worked in terminal
            yt_cmd = [
                'yt-dlp',
                '-f', 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                '--merge-output-format', 'mp4',
                '-o', output_path,
                '--no-playlist',
                '--no-check-certificate'
            ]
            
            # Add cookies if available and not using Tor
            if not self.use_tor and self.cookies_path and os.path.exists(self.cookies_path):
                yt_cmd.extend(['--cookies', self.cookies_path])
            
            # Add Tor proxy if enabled
            if self.use_tor:
                # self._ensure_tor_running()
                yt_cmd.extend([
                    '--proxy', 'socks5://localhost:9050',
                    '--socket-timeout', '60',
                    '--retries', '10',
                    '--force-ipv4',
                ])
            
            # Finally add the URL
            yt_cmd.append(url)
            
            logger.info(f"Downloading YouTube video: {url}")
            logger.info(f"Output path: {output_path}")
            logger.info(f"Full command: {' '.join(yt_cmd)}")
            
            # Run the download
            result = subprocess.run(yt_cmd, capture_output=True, text=True)
            
            # Check if download was successful
            if result.returncode == 0:
                if Path(output_path).exists():
                    file_size = os.path.getsize(output_path) / (1024 * 1024)
                    logger.info(f"YouTube download completed: {output_path} ({file_size:.2f} MB)")
                    logger.debug(f"Download output: {result.stdout}")
                    return str(Path(output_path).absolute())
                else:
                    # Try alternative output pattern
                    alt_output = Path(f"{filename}.mp4.part")
                    if alt_output.exists():
                        alt_output.rename(output_path)
                        file_size = os.path.getsize(output_path) / (1024 * 1024)
                        logger.info(f"YouTube download completed (renamed from .part): {output_path} ({file_size:.2f} MB)")
                        return str(Path(output_path).absolute())
            
            # If we get here, something went wrong
            logger.error(f"Download failed with return code: {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            
            # Try with simpler format selector as fallback
            logger.info("Trying fallback with simpler format selector...")
            fallback_cmd = [
                'yt-dlp',
                '-f', 'mp4',
                '-o', output_path,
                '--no-playlist',
                url
            ]
            
            if not self.use_tor and self.cookies_path and os.path.exists(self.cookies_path):
                fallback_cmd.extend(['--cookies', self.cookies_path])
            
            fallback_result = subprocess.run(fallback_cmd, capture_output=True, text=True)
            
            if fallback_result.returncode == 0 and Path(output_path).exists():
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"Fallback download succeeded: {output_path} ({file_size:.2f} MB)")
                return str(Path(output_path).absolute())
            
            return None

        except Exception as e:
            logger.exception(f"Critical error in download: {str(e)}")
            return None
