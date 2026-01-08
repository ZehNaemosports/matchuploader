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
        quality: str = '720',
        cookies_path: Optional[str] = "/home/ubuntu/cookies.txt",
        use_tor: bool = False,
    ):
        self.quality = quality
        self.cookies_path = cookies_path
        self.use_tor = use_tor

    def set_quality(self, quality: str):
        self.quality = quality

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
        """
        Base yt-dlp command used everywhere.
        This guarantees:
        - JS runtime
        - Cookies
        - Tor (if enabled)
        """
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--js-runtimes", "deno",
        ]

        # ALWAYS use cookies if available (Tor or not)
        if self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(["--cookies", self.cookies_path])

        if self.use_tor:
            # self._ensure_tor_running()
            cmd.extend([
                "--proxy", "socks5://localhost:9050",
                "--socket-timeout", "60",
                "--retries", "10",
                "--force-ipv4",
            ])

        return cmd

    async def list_formats(self, url: str):
        try:
            cmd = self._build_base_command() + ["--list-formats", url]

            logger.info(f"Listing available formats for: {url}")
            logger.info(f"Command: {' '.join(cmd)}")

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

    async def download(self, url: str, filename: str) -> Optional[str]:
        try:
            await self.list_formats(url)

            output_path = f"{filename}.mp4"

            # -------------------------
            # VEO HANDLING
            # -------------------------
            if "app.veo.co" in url:
                veo_cmd = self._build_base_command() + [
                    "-f", "standard-1080p",
                    "--merge-output-format", "mp4",
                    "-o", output_path,
                    "--no-check-certificate",
                    url,
                ]

                logger.info(f"Downloading Veo video")
                logger.info(f"Command: {' '.join(veo_cmd)}")

                result = subprocess.run(
                    veo_cmd,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0 and Path(output_path).exists():
                    size = os.path.getsize(output_path) / (1024 * 1024)
                    logger.info(f"Veo download completed: {size:.2f} MB")
                    return str(Path(output_path).absolute())

                logger.error(f"Veo download failed: {result.stderr}")
                return None

            # -------------------------
            # YOUTUBE DOWNLOAD
            # -------------------------
            yt_cmd = self._build_base_command() + [
                "-f", f"bestvideo[height<={self.quality}]+bestaudio/best[height<={self.quality}]",
                "--merge-output-format", "mp4",
                "-o", output_path,
                "--no-check-certificate",
                url,
            ]

            logger.info(f"Downloading YouTube video")
            logger.info(f"Output path: {output_path}")
            logger.info(f"Command: {' '.join(yt_cmd)}")

            result = subprocess.run(
                yt_cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and Path(output_path).exists():
                size = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"YouTube download completed: {size:.2f} MB")
                return str(Path(output_path).absolute())

            logger.error(f"Download failed: {result.stderr}")

            # -------------------------
            # FALLBACK
            # -------------------------
            logger.info("Trying fallback format selector")

            fallback_cmd = self._build_base_command() + [
                "-f", "mp4",
                "-o", output_path,
                url,
            ]

            logger.info(f"Fallback command: {' '.join(fallback_cmd)}")

            fallback_result = subprocess.run(
                fallback_cmd,
                capture_output=True,
                text=True,
            )

            if fallback_result.returncode == 0 and Path(output_path).exists():
                size = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"Fallback download succeeded: {size:.2f} MB")
                return str(Path(output_path).absolute())

            logger.error("Fallback also failed")
            return None

        except Exception as e:
            logger.exception(f"Critical error in download: {e}")
            return None
