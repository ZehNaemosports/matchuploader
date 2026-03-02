import subprocess
from pathlib import Path
from typing import Optional
import os
import logging
import re

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
        facebook_cookies_path: Optional[str] = "/home/ubuntu/facebookcookies.txt",
        use_tor: bool = False,
        use_remote_components: bool = False,
        auto_update_components: bool = False,
    ):
        self.preferred_quality = preferred_quality
        self.fallback_quality = '720'
        self.cookies_path = cookies_path
        self.facebook_cookies_path = facebook_cookies_path
        self.use_tor = use_tor
        self.use_remote_components = use_remote_components

        if auto_update_components:
            self._update_components_sync()

    def _update_components_sync(self):
        try:
            logger.info("Updating yt-dlp...")
            subprocess.run(["yt-dlp", "-U"], capture_output=True, text=True, timeout=30)
        except Exception as e:
            logger.warning(f"Could not update yt-dlp: {e}")

    def _build_base_command(self, is_facebook: bool = False):
        cmd = ["yt-dlp", "--no-playlist"]

        if self.use_remote_components and not is_facebook:
            cmd.extend(["--remote-components", "ejs:github"])

        # Cookies
        if is_facebook and self.facebook_cookies_path and os.path.exists(self.facebook_cookies_path):
            cmd.extend(["--cookies", self.facebook_cookies_path])
        elif self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(["--cookies", self.cookies_path])

        # Facebook headers
        if is_facebook:
            cmd.extend([
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--referer", "https://www.facebook.com/",
            ])

        if self.use_tor:
            cmd.extend(["--proxy", "socks5://127.0.0.1:9050"])

        return cmd

    def _normalize_drive_url(self, url: str) -> str:
        """
        Converts:
        https://drive.google.com/file/d/<ID>/view?...
        into:
        https://drive.google.com/uc?id=<ID>
        """
        match = re.search(r'/file/d/([^/]+)/', url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?id={file_id}"
        return url

    async def list_formats(self, url: str):
        try:
            is_facebook = 'facebook.com' in url
            is_drive = 'drive.google.com' in url

            if is_drive:
                url = self._normalize_drive_url(url)

            cmd = self._build_base_command(is_facebook=is_facebook) + ["-F", url]

            logger.info(f"RUNNING FORMAT LIST CMD: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return result.stdout

            logger.warning(f"Format listing failed: {result.stderr[:300]}")
            return None

        except Exception as e:
            logger.error(f"Format listing error: {e}")
            return None

    async def _download_facebook(self, url: str, filename: str) -> Optional[str]:
        try:
            logger.info(f"[FACEBOOK] Downloading: {url}")

            output_pattern = f"{filename}.%(ext)s"
            cmd = self._build_base_command(is_facebook=True)

            cmd.extend([
                "-f", "best",
                "--merge-output-format", "mp4",
                "-o", output_pattern,
                url
            ])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            actual_output = self._find_output_file(filename, result.stdout + result.stderr)

            if actual_output and Path(actual_output).exists():
                return str(Path(actual_output).absolute())

            return None

        except Exception as e:
            logger.error(f"Facebook error: {e}")
            return None

    async def _download_google_drive(self, url: str, filename: str) -> Optional[str]:
        try:
            logger.info(f"[GOOGLE DRIVE] Downloading: {url}")

            url = self._normalize_drive_url(url)
            output_pattern = f"{filename}.%(ext)s"

            cmd = self._build_base_command()

            cmd.extend([
                "-f", "best",
                "--merge-output-format", "mp4",
                "-o", output_pattern,
                url
            ])

            logger.info(f"RUNNING CMD: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
            actual_output = self._find_output_file(filename, result.stdout + result.stderr)

            if actual_output and Path(actual_output).exists():
                logger.info(f"Drive download success: {actual_output}")
                return str(Path(actual_output).absolute())

            logger.warning(f"Drive download failed: {result.stderr[:300]}")
            return None

        except Exception as e:
            logger.exception(f"Google Drive error: {e}")
            return None

    async def download(self, url: str, filename: str) -> Optional[str]:
        try:
            if "facebook.com" in url:
                return await self._download_facebook(url, filename)

            if "drive.google.com" in url:
                return await self._download_google_drive(url, filename)

            logger.info(f"[YOUTUBE/GENERIC] Downloading: {url}")

            output_pattern = f"{filename}.%(ext)s"

            qualities_to_try = [
                self.preferred_quality,
                self.fallback_quality,
                None
            ]

            for quality in qualities_to_try:
                cmd = self._build_base_command()

                if quality:
                    format_spec = (
                        f"bestvideo[height<={quality}][vcodec^=avc1]"
                        f"+bestaudio[acodec^=mp4a]"
                        f"/bestvideo[height<={quality}]+bestaudio"
                        f"/best[height<={quality}]"
                    )
                else:
                    format_spec = "bestvideo+bestaudio/best"

                cmd.extend([
                    "-f", format_spec,
                    "--merge-output-format", "mp4",
                    "-o", output_pattern,
                    url
                ])

                logger.info(f"RUNNING CMD: {' '.join(cmd)}")

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
                actual_output = self._find_output_file(filename, result.stdout + result.stderr)

                if actual_output and Path(actual_output).exists():
                    logger.info(f"Download success: {actual_output}")
                    return str(Path(actual_output).absolute())

                logger.warning(f"Quality {quality} failed, trying fallback...")

            return None

        except Exception as e:
            logger.exception(f"Download error: {e}")
            return None

    def _find_output_file(self, base_filename: str, ytdlp_output: str) -> Optional[str]:
        try:
            merge_match = re.search(r'Merging formats into "([^"]+\.(?:mp4|webm|mkv))"', ytdlp_output)
            if merge_match:
                return merge_match.group(1)

            dest_matches = re.findall(r'Destination:\s+([^\s]+\.(?:mp4|webm|mkv))', ytdlp_output)
            if dest_matches:
                return dest_matches[-1]

            for ext in ['.mp4', '.webm', '.mkv']:
                candidate = f"{base_filename}{ext}"
                if Path(candidate).exists():
                    return candidate

            return None
        except Exception:
            return None