import subprocess
from pathlib import Path
from typing import Optional
import time
import os
import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YoutubeDownloader:
    def __init__(self, quality='720', cookies_path: Optional[str] = "/home/ubuntu/cookies.txt", use_tor=True):
        self.quality = quality
        self.cookies_path = cookies_path
        self.use_tor = use_tor
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]

    def set_quality(self, quality):
        self.quality = quality

    def _ensure_tor_running(self):
        try:
            subprocess.run(["systemctl", "is-active", "--quiet", "tor"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(["sudo", "service", "tor", "start"], check=True)
            time.sleep(3)
            logger.info("Tor service started")

    def _build_base_command(self):
        """Build common command arguments with enhanced anti-detection"""
        cmd = ['yt-dlp', '--no-playlist']
        
        # Add random user agent
        user_agent = random.choice(self.user_agents)
        cmd.extend(['--user-agent', user_agent])
        
        if self.use_tor:
            cmd.extend([
                '--proxy', 'socks5://localhost:9050',
                '--socket-timeout', '90',
                '--retries', '15',
                '--force-ipv4',
                '--throttled-rate', '100K',
                '--sleep-requests', '2',
                '--sleep-interval', '5',
                '--max-sleep-interval', '10',
            ])
            
        if self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(['--cookies', self.cookies_path])
            
        # Additional anti-detection options
        cmd.extend([
            '--extractor-retries', '3',
            '--ignore-errors',
            '--no-call-home',
            '--no-check-certificate',
            '--compat-options', 'youtube-dl',
        ])
            
        return cmd

    async def list_formats(self, url: str):
        """List available formats for a YouTube video"""
        try:
            base_cmd = self._build_base_command()
            list_cmd = base_cmd + ['--list-formats', url]
            
            logger.info(f"Listing available formats for: {url}")
            
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("Successfully retrieved format information")
                return result.stdout
            else:
                logger.error(f"Failed to list formats: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout while listing formats")
            return None
        except Exception as e:
            logger.exception(f"Error listing formats: {str(e)}")
            return None

    async def download(self, url: str, filename: str) -> Optional[str]:
        max_retries = 3
        retry_delay = 10
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Download attempt {attempt + 1}/{max_retries}")
                
                base_cmd = self._build_base_command()
                output_path = f"{filename}.mp4"
                
                # Remove existing file if it exists
                if Path(output_path).exists():
                    Path(output_path).unlink()
                
                # For YouTube videos, use a more robust format selection
                if "youtube.com" in url or "youtu.be" in url:
                    # Try different format selectors
                    format_selectors = [
                        f'bestvideo[height<={self.quality}][vcodec^=avc1]+bestaudio/best[height<={self.quality}]',
                        f'best[height<={self.quality}]',
                        'best',
                        'worst'  # Sometimes lower quality works better
                    ]
                    
                    for format_selector in format_selectors:
                        yt_cmd = base_cmd + [
                            '-f', format_selector,
                            '--merge-output-format', 'mp4',
                            '--embed-thumbnail',
                            '--embed-metadata',
                            '--audio-quality', '0',
                            '--progress',
                            '--no-part',
                            '--concurrent-fragments', '2',  # Reduce concurrent fragments
                            '-o', output_path,
                            url
                        ]
                        
                        logger.info(f"Trying format selector: {format_selector}")
                        logger.info(f"Command: {' '.join(yt_cmd)}")
                        
                        result = subprocess.run(yt_cmd, capture_output=True, text=True, timeout=300)
                        
                        if Path(output_path).exists() and os.path.getsize(output_path) > 0:
                            file_size = os.path.getsize(output_path) / (1024 * 1024)
                            logger.info(f"Download completed: {output_path} ({file_size:.2f} MB)")
                            return str(Path(output_path).absolute())
                        else:
                            logger.warning(f"Format selector '{format_selector}' failed, trying next...")
                            if Path(output_path).exists():
                                Path(output_path).unlink()
                
                # If all format selectors failed
                logger.error("All format selectors failed")
                if result.stderr:
                    logger.error(f"Error details: {result.stderr}")
                
            except subprocess.TimeoutExpired:
                logger.error(f"Download timeout on attempt {attempt + 1}")
                if Path(output_path).exists():
                    Path(output_path).unlink()
            except Exception as e:
                logger.exception(f"Error in download attempt {attempt + 1}: {str(e)}")
                if Path(output_path).exists():
                    Path(output_path).unlink()
            
            # Wait before retry
            if attempt < max_retries - 1:
                logger.info(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        return None
