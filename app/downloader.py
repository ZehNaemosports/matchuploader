import subprocess
from pathlib import Path
from typing import Optional
import os
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class YoutubeDownloader:

    def __init__(
        self,
        preferred_quality: str = "1080",
        cookies_path: Optional[str] = "/home/ubuntu/cookies.txt",
        facebook_cookies_path: Optional[str] = "/home/ubuntu/facebookcookies.txt",
        use_tor: bool = False,
    ):
        self.preferred_quality = preferred_quality
        self.fallback_quality = "720"
        self.cookies_path = cookies_path
        self.facebook_cookies_path = facebook_cookies_path
        self.use_tor = use_tor

    # --------------------------------------------------------
    # Base yt-dlp command
    # --------------------------------------------------------

    def _build_base_command(self, is_facebook=False):

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--newline",
            "--progress",
            "--retries", "10",
            "--fragment-retries", "10",
            "--remote-components", "ejs:github",
            "--extractor-args", "youtube:player_client=android,web"
        ]

        # cookies
        if is_facebook and self.facebook_cookies_path and os.path.exists(self.facebook_cookies_path):
            cmd.extend(["--cookies", self.facebook_cookies_path])

        elif self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(["--cookies", self.cookies_path])

        # facebook headers
        if is_facebook:
            cmd.extend([
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "--referer",
                "https://www.facebook.com/"
            ])

        if self.use_tor:
            cmd.extend(["--proxy", "socks5://127.0.0.1:9050"])

        return cmd

    # --------------------------------------------------------
    # Normalize Google Drive URLs
    # --------------------------------------------------------

    def _normalize_drive_url(self, url: str):

        match = re.search(r"/file/d/([^/]+)/", url)

        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?id={file_id}"

        return url

    # --------------------------------------------------------
    # Format listing
    # --------------------------------------------------------

    async def list_formats(self, url: str):

        try:

            is_facebook = "facebook.com" in url
            is_drive = "drive.google.com" in url

            if is_drive:
                url = self._normalize_drive_url(url)

            cmd = self._build_base_command(is_facebook=is_facebook)

            cmd.extend(["-F", url])

            logger.info(f"FORMAT LIST COMMAND:\n{' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            logger.info("yt-dlp stdout:")
            logger.info(result.stdout)

            if result.stderr:
                logger.warning("yt-dlp stderr:")
                logger.warning(result.stderr)

            logger.info(f"Return code: {result.returncode}")

            if result.returncode == 0:
                return result.stdout

            return None

        except Exception as e:
            logger.exception(f"Format listing error: {e}")
            return None

    # --------------------------------------------------------
    # Google Drive
    # --------------------------------------------------------

    async def _download_google_drive(self, url: str, filename: str):

        try:

            url = self._normalize_drive_url(url)

            output_pattern = f"{filename}.%(ext)s"

            cmd = self._build_base_command()

            cmd.extend([
                "-f",
                "best",
                "--merge-output-format",
                "mp4",
                "-o",
                output_pattern,
                url
            ])

            logger.info(f"RUNNING CMD:\n{' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1200
            )

            logger.info(result.stdout)

            if result.stderr:
                logger.warning(result.stderr)

            logger.info(f"Return code: {result.returncode}")

            output_text = result.stdout + result.stderr

            actual_output = self._find_output_file(filename, output_text)

            if actual_output and Path(actual_output).exists():
                logger.info(f"Drive download success: {actual_output}")
                return str(Path(actual_output).absolute())

            logger.error("Drive download failed: output file not detected")

            return None

        except Exception as e:
            logger.exception(f"Google Drive error: {e}")
            return None

    # --------------------------------------------------------
    # Facebook
    # --------------------------------------------------------

    async def _download_facebook(self, url: str, filename: str):

        try:

            output_pattern = f"{filename}.%(ext)s"

            cmd = self._build_base_command(is_facebook=True)

            cmd.extend([
                "-f",
                "best",
                "--merge-output-format",
                "mp4",
                "-o",
                output_pattern,
                url
            ])

            logger.info(f"RUNNING CMD:\n{' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1200
            )

            logger.info(result.stdout)

            if result.stderr:
                logger.warning(result.stderr)

            logger.info(f"Return code: {result.returncode}")

            output_text = result.stdout + result.stderr

            actual_output = self._find_output_file(filename, output_text)

            if actual_output and Path(actual_output).exists():
                logger.info(f"Facebook download success: {actual_output}")
                return str(Path(actual_output).absolute())

            logger.error("Facebook download failed: output file not detected")

            return None

        except Exception as e:
            logger.exception(f"Facebook download error: {e}")
            return None

    # --------------------------------------------------------
    # Main download
    # --------------------------------------------------------

    async def download(self, url: str, filename: str):

        try:

            if "facebook.com" in url:
                return await self._download_facebook(url, filename)

            if "drive.google.com" in url:
                return await self._download_google_drive(url, filename)

            logger.info(f"[YOUTUBE] Downloading: {url}")

            output_pattern = f"{filename}.%(ext)s"

            qualities_to_try = [
                self.preferred_quality,
                self.fallback_quality,
                None
            ]

            for quality in qualities_to_try:

                cmd = self._build_base_command()

                if quality:

                    format_spec = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

                else:

                    format_spec = "bestvideo+bestaudio/best"

                cmd.extend([
                    "-f",
                    format_spec,
                    "--merge-output-format",
                    "mp4",
                    "-o",
                    output_pattern,
                    url
                ])

                logger.info(f"RUNNING CMD:\n{' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=1800
                )

                logger.info(result.stdout)

                if result.stderr:
                    logger.warning(result.stderr)

                logger.info(f"Return code: {result.returncode}")

                output_text = result.stdout + result.stderr

                actual_output = self._find_output_file(filename, output_text)

                if actual_output and Path(actual_output).exists():
                    logger.info(f"Download success: {actual_output}")
                    return str(Path(actual_output).absolute())

                logger.warning(f"Download failed for quality {quality}")

            logger.error("All download attempts failed")

            return None

        except Exception as e:
            logger.exception(f"Download error: {e}")
            return None

    # --------------------------------------------------------
    # Detect output file
    # --------------------------------------------------------

    def _find_output_file(self, base_filename: str, ytdlp_output: str):

        try:

            merge_match = re.search(
                r'Merging formats into "([^"]+\.(?:mp4|webm|mkv))"',
                ytdlp_output
            )

            if merge_match:
                return merge_match.group(1)

            dest_matches = re.findall(
                r"Destination:\s+([^\s]+\.(?:mp4|webm|mkv))",
                ytdlp_output
            )

            if dest_matches:
                return dest_matches[-1]

            for ext in [".mp4", ".webm", ".mkv"]:

                candidate = f"{base_filename}{ext}"

                if Path(candidate).exists():
                    return candidate

            return None

        except Exception:
            return None