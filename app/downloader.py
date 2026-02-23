import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import time
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
            use_tor: bool = True,
            use_remote_components: bool = True,
            auto_update_components: bool = True,
    ):
        self.preferred_quality = preferred_quality
        self.fallback_quality = '720'
        self.cookies_path = cookies_path
        self.facebook_cookies_path = facebook_cookies_path
        self.use_tor = use_tor
        self.use_remote_components = use_remote_components
        self.auto_update_components = auto_update_components

        if auto_update_components:
            self._update_components_sync()

    def _update_components_sync(self):
        try:
            logger.info("Updating EJS components...")
            cmd = ["yt-dlp", "--remote-components", "ejs:github"]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception as e:
            logger.warning(f"Could not update EJS components: {e}")

    def _build_base_command(self, include_components: bool = True, is_facebook: bool = False):
        cmd = ["yt-dlp", "--no-playlist"]

        if not is_facebook:
            cmd.extend([
                "--js-runtimes", "deno",
                # Bypass: Use the iOS player client which is less restricted
                "--extractor-args", "youtube:player_client=ios,web"
            ])

        if self.use_remote_components and include_components and not is_facebook:
            cmd.extend(["--remote-components", "ejs:github"])

        if is_facebook and self.facebook_cookies_path and os.path.exists(self.facebook_cookies_path):
            cmd.extend(["--cookies", self.facebook_cookies_path])
        elif self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(["--cookies", self.cookies_path])

        if is_facebook:
            cmd.extend([
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--referer", "https://www.facebook.com/",
                "--add-header", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            ])

        if self.use_tor:
            # Added proxy log for visibility
            cmd.extend(["--proxy", "socks5://127.0.0.1:9050"])

        return cmd

    async def list_formats(self, url: str):
        try:
            is_facebook = 'facebook.com' in url
            cmd = self._build_base_command(is_facebook=is_facebook) + ["-F", url]

            # COMMAND LOG
            logger.info(f"RUNNING FORMAT LIST CMD: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if result.returncode == 0:
                return result.stdout
            logger.warning(f"Failed to retrieve formats. Error: {result.stderr[:200]}")
            return None
        except Exception as e:
            logger.error(f"Error listing formats: {e}")
            return None

    async def _download_veo(self, url: str, filename: str) -> Optional[str]:
        try:
            logger.info(f"--- [VEO] Processing: {url} ---")
            formats_output = await self.list_formats(url)
            if formats_output: logger.info(f"Available Veo formats:\n{formats_output}")

            output_pattern = f"{filename}.%(ext)s"
            veo_qualities = ["standard-1080p", "standard-720p",
                             "bestvideo[format_id^=standard]+bestaudio/best[format_id^=standard]"]

            for quality in veo_qualities:
                veo_cmd = self._build_base_command(include_components=False, is_facebook=False)
                veo_cmd.extend(
                    ["-f", quality, "--merge-output-format", "mp4", "-o", output_pattern, "--no-check-certificate",
                     "--no-continue", url])

                # COMMAND LOG
                logger.info(f"RUNNING VEO DOWNLOAD CMD: {' '.join(veo_cmd)}")

                result = subprocess.run(veo_cmd, capture_output=True, text=True, timeout=1800)
                actual_output = self._find_output_file(filename, result.stdout + result.stderr)
                if actual_output and Path(actual_output).exists():
                    return str(Path(actual_output).absolute())
            return None
        except Exception as e:
            logger.error(f"Veo failed: {e}")
            return None

    async def _download_facebook(self, url: str, filename: str, timeout: int) -> Optional[str]:
        try:
            logger.info(f"--- [FACEBOOK] Processing: {url} ---")
            output_pattern = f"{filename}.%(ext)s"
            cmd = self._build_base_command(is_facebook=True)
            cmd.extend(["-o", output_pattern, "--merge-output-format", "mp4", url])

            # COMMAND LOG
            logger.info(f"RUNNING FACEBOOK DOWNLOAD CMD: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            actual_output = self._find_output_file(filename, result.stdout + result.stderr)
            return str(Path(actual_output).absolute()) if actual_output else None
        except Exception as e:
            logger.error(f"Facebook error: {e}")
            return None

    async def download(self, url: str, filename: str) -> Optional[str]:
        try:
            if "app.veo.co" in url: return await self._download_veo(url, filename)
            if "facebook.com" in url: return await self._download_facebook(url, filename, 300)

            logger.info(f"--- [YOUTUBE/GENERIC] Processing: {url} ---")
            formats_output = await self.list_formats(url)
            if formats_output: logger.info(f"Available YouTube formats:\n{formats_output}")

            output_pattern = f"{filename}.%(ext)s"
            qualities_to_try = [(self.preferred_quality, "preferred"), (self.fallback_quality, "fallback"),
                                (None, "any")]

            for quality, name in qualities_to_try:
                cmd = self._build_base_command(is_facebook=False)
                if quality:
                    format_spec = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best"
                    cmd.extend(["-f", format_spec, "--merge-output-format", "mp4"])
                else:
                    cmd.extend(["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"])

                cmd.extend(["-o", output_pattern, "--no-check-certificate", url])

                # COMMAND LOG
                logger.info(f"RUNNING YOUTUBE DOWNLOAD CMD ({name}): {' '.join(cmd)}")

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                actual_output = self._find_output_file(filename, result.stdout + result.stderr)
                if actual_output and Path(actual_output).exists():
                    return str(Path(actual_output).absolute())
            return None
        except Exception as e:
            logger.exception(f"General download error: {e}")
            return None

    def _find_output_file(self, base_filename: str, ytdlp_output: str) -> Optional[str]:
        try:
            merge_match = re.search(r'Merging formats into "([^"]+\.(?:mp4|webm|mkv))"', ytdlp_output)
            if merge_match: return merge_match.group(1)
            dest_matches = re.findall(r'Destination:\s+([^\s]+\.(?:mp4|webm|mkv))', ytdlp_output)
            if dest_matches: return dest_matches[-1]
            for ext in ['.mp4', '.webm', '.mkv']:
                if Path(f"{base_filename}{ext}").exists(): return f"{base_filename}{ext}"
            return None
        except Exception:
            return None