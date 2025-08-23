import subprocess
from pathlib import Path
from typing import Optional
import time
import os
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
class YoutubeDownloader:
    def _init_(self, quality='1080', cookies_path: Optional[str] = "/home/ubuntu/cookies.txt", use_tor=True):
        self.quality = quality
        self.cookies_path = cookies_path
        self.use_tor = use_tor

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
        cmd = ['yt-dlp', '--no-playlist']
        
        if self.use_tor:
            self._ensure_tor_running()
            cmd.extend([
                '--proxy', 'socks5://localhost:9050',
                '--socket-timeout', '60',
                '--retries', '10',
                '--force-ipv4',
                '--extractor-args', 'youtube:player_client=android',
                '--throttled-rate', '100K'
            ])
            
        if not self.use_tor and self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(['--cookies', self.cookies_path])
            
        return cmd

    def _probe_available_formats(self, url: str) -> Optional[str]:
        """Probe available formats and return the best compatible format string"""
        try:
            probe_cmd = self._build_base_command() + [
                '-F',
                '--no-simulate',
                url
            ]
            
            # Remove potentially problematic flags for probing
            probe_cmd = [arg for arg in probe_cmd if arg not in ['--no-playlist', '--remux-video']]
            
            logger.info(f"Probing available formats for: {url}")
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"Format probe failed: {result.stderr}")
                return None
                
            # Analyze available formats
            lines = result.stdout.split('\n')
            compatible_formats = []
            
            for line in lines:
                if any(x in line for x in ['avc1', 'mp4a', 'm4a', 'mp4', 'h264']):
                    compatible_formats.append(line.strip())
            
            if compatible_formats:
                logger.info(f"Compatible MP4 formats found ({len(compatible_formats)}):")
                for fmt in compatible_formats[:5]:
                    logger.info(f"  {fmt}")
            
            return result.stdout
            
        except Exception as e:
            logger.warning(f"Format probe failed: {str(e)}")
            return None

    async def download(self, url: str, filename: str) -> Optional[str]:
        try:
            base_cmd = self._build_base_command()
            output_path = f"{filename}.mp4"
            
            # Clean up any existing partial files
            if Path(output_path).exists():
                Path(output_path).unlink()
            
            if "app.veo.co" in url:
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
                    return Path(output_path).absolute()
                
                logger.error(f"Veo download failed: {result.stderr}")
                return None
            
            format_info = self._probe_available_formats(url)
            
            yt_cmd = base_cmd + [
                '-f', (
                    f'(bestvideo[height<={self.quality}][ext=mp4][vcodec^=avc1]/'
                    f'bestvideo[height<={self.quality}][ext=mp4]/'
                    f'bestvideo[height<={self.quality}][vcodec^=avc1])'
                    f'+bestaudio[ext=m4a]/'
                    f'best[height<={self.quality}][ext=mp4]/'
                    f'best[ext=mp4]'
                ),
                '--remux-video', 'mp4',
                '--embed-thumbnail',
                '--embed-metadata',
                '--audio-quality', '0',
                '--no-part',
                '--concurrent-fragments', '4',
                '-o', output_path,
                '--verbose',  
                url
            ]
            
            logger.info(f"Downloading YouTube video: {url}")
            logger.info(f"Format selection strategy: MP4-compatible only (H.264 + AAC)")
            
            result = subprocess.run(yt_cmd, capture_output=True, text=True)
            
            # Parse yt-dlp output to see what format was actually selected
            if result.stdout:
                format_match = re.search(r'\[info\]\s+(\[download\].format.)', result.stdout)
                if format_match:
                    logger.info(f"Selected format: {format_match.group(1)}")
            
            if Path(output_path).exists():
                file_size = os.path.getsize(output_path) / (1024 * 1024) 
                logger.info(f"YouTube download completed: {output_path} ({file_size:.2f} MB)")
                return Path(output_path).absolute()
                
            logger.error("Error downloading video - no output file created")
            if result.stderr:
                logger.error(f"Error details: {result.stderr}")
            if result.stdout:
                logger.error(f"Process output: {result.stdout}")
                
            return None

        except subprocess.TimeoutExpired:
            logger.error(f"Download timed out after 1 hour: {url}")
            return None
        except Exception as e:
            logger.exception(f"Critical error in download: {str(e)}")
            return None