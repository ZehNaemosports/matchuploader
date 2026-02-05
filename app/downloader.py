import subprocess
from pathlib import Path
from typing import Optional
import time
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YoutubeDownloader:
    def __init__(
        self,
        preferred_quality: str = '1080',
        cookies_path: Optional[str] = "/home/ubuntu/cookies.txt",
        use_tor: bool = False,
        debug_formats: bool = False,
    ):
        self.preferred_quality = preferred_quality
        self.fallback_quality = '720'
        self.cookies_path = cookies_path
        self.use_tor = use_tor
        self.debug_formats = debug_formats

    def set_quality(self, preferred_quality: str, fallback_quality: str = '720'):
        self.preferred_quality = preferred_quality
        self.fallback_quality = fallback_quality

    def _ensure_tor_running(self):
        try:
            subprocess.run(
                ["systemctl", "is-active", "--quiet", "tor"],
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(
                ["sudo", "service", "tor", "start"],
                check=True,
            )
            time.sleep(3)
            logger.info("Tor service started")

    def _build_base_command(self):
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--extractor-retries", "5",
            "--fragment-retries", "5",
            "--retries", "5",
        ]

        if self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(["--cookies", self.cookies_path])

        if self.use_tor:
            cmd.extend([
                "--proxy", "socks5://localhost:9050",
                "--socket-timeout", "60",
                "--force-ipv4",
            ])

        return cmd

    async def list_formats(self, url: str):
        try:
            cmd = self._build_base_command() + ["--list-formats", url]

            logger.info(f"Listing available formats for: {url}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info(f"Available formats:\n{result.stdout}")
                return result.stdout

            logger.error(f"Failed to list formats: {result.stderr}")
            return None

        except Exception as e:
            logger.exception(f"Error listing formats: {e}")
            return None

    def _valid_file(self, path: str):
        return Path(path).exists() and os.path.getsize(path) > 0

    async def download(self, url: str, filename: str) -> Optional[str]:
        try:
            if self.debug_formats:
                await self.list_formats(url)

            output_path = f"{filename}.mp4"

            # -------------------------
            # VEO HANDLING
            # -------------------------
            if "app.veo.co" in url:
                veo_cmd = self._build_base_command()

                veo_cmd.extend([
                    "-f", "standard-1080p",
                    "--merge-output-format", "mp4",
                    "-o", output_path,
                    url,
                ])

                logger.info("Downloading Veo video")
                result = subprocess.run(
                    veo_cmd,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0 and self._valid_file(output_path):
                    return str(Path(output_path).absolute())

                logger.error(f"Veo download failed: {result.stderr}")
                return None

            # -------------------------
            # YOUTUBE DOWNLOAD
            # -------------------------

            preferred_cmd = self._build_base_command() + [
                "-f", f"bestvideo[height<={self.preferred_quality}]+bestaudio/best[height<={self.preferred_quality}]",
                "--merge-output-format", "mp4",
                "-o", output_path,
                url,
            ]

            logger.info(f"Trying preferred quality {self.preferred_quality}p")

            result = subprocess.run(
                preferred_cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and self._valid_file(output_path):
                return str(Path(output_path).absolute())

            logger.warning("Preferred quality failed")

            if Path(output_path).exists():
                os.remove(output_path)

            fallback_cmd = self._build_base_command() + [
                "-f", f"bestvideo[height<={self.fallback_quality}]+bestaudio/best[height<={self.fallback_quality}]",
                "--merge-output-format", "mp4",
                "-o", output_path,
                url,
            ]

            logger.info(f"Trying fallback quality {self.fallback_quality}p")

            fallback_result = subprocess.run(
                fallback_cmd,
                capture_output=True,
                text=True,
            )

            if fallback_result.returncode == 0 and self._valid_file(output_path):
                return str(Path(output_path).absolute())

            logger.warning("Fallback failed")

            if Path(output_path).exists():
                os.remove(output_path)

            last_resort_cmd = self._build_base_command() + [
                "-f", "mp4",
                "-o", output_path,
                url,
            ]

            logger.info("Trying last resort mp4 format")

            last_resort_result = subprocess.run(
                last_resort_cmd,
                capture_output=True,
                text=True,
            )

            if last_resort_result.returncode == 0 and self._valid_file(output_path):
                return str(Path(output_path).absolute())

            logger.error("All download attempts failed")
            return None

        except Exception as e:
            logger.exception(f"Critical error in download: {e}")
            return None
