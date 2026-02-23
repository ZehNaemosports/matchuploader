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
            use_tor: bool = False,
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

    def set_quality(self, preferred_quality: str, fallback_quality: str = '720'):
        self.preferred_quality = preferred_quality
        self.fallback_quality = fallback_quality

    def _update_components_sync(self):
        """Synchronous component update without the internal --update flag (use pip instead)"""
        try:
            logger.info("Updating EJS components...")
            cmd = [
                "yt-dlp",
                "--remote-components", "ejs:github",
                # Removed --update to avoid pip conflict
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception as e:
            logger.warning(f"Could not update EJS components: {e}")

    def _build_base_command(self, include_components: bool = True, is_facebook: bool = False):
        cmd = ["yt-dlp", "--no-playlist"]

        if not is_facebook:
            cmd.extend(["--js-runtimes", "deno"])

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
        else:
            # Generic high-quality User-Agent for Veo/YouTube
            cmd.extend(["--user-agent",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"])

        if self.use_tor:
            cmd.extend(["--proxy", "socks5://localhost:9050", "--socket-timeout", "60"])

        return cmd

    async def list_formats(self, url: str):
        try:
            is_facebook = 'facebook.com' in url
            cmd = self._build_base_command(is_facebook=is_facebook) + ["-F", url]
            logger.info(f"Checking available formats for: {url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            logger.error(f"Error listing formats: {e}")
            return None

    async def _download_veo(self, url: str, filename: str) -> Optional[str]:
        """Handle Veo video downloads targeting Standard broadcast views over Panorama."""
        try:
            logger.info(f"--- Starting Veo Download Process for: {url} ---")

            # 1. Log formats so you can see what is available
            formats_output = await self.list_formats(url)
            if formats_output:
                logger.info(f"Available formats for this match:\n{formats_output}")
            else:
                logger.warning("Could not retrieve format list. Proceeding with generic 'best' attempt.")

            output_pattern = f"{filename}.%(ext)s"

            # 2. Define priority: Target 'standard' (AI Follow) first.
            # Avoid 'panorama' unless it's the only option.
            veo_qualities = [
                "standard-1080p",
                "standard-720p",
                "bestvideo[format_id^=standard]+bestaudio/best[format_id^=standard]",
                "bestvideo+bestaudio/best"  # Final fallback (might pick panorama)
            ]

            for quality in veo_qualities:
                logger.info(f"Attempting Veo download with format selector: {quality}")

                veo_cmd = self._build_base_command(include_components=False, is_facebook=False)
                veo_cmd.extend([
                    "-f", quality,
                    "--merge-output-format", "mp4",
                    "-o", output_pattern,
                    "--no-check-certificate",
                    "--no-continue",  # Fresh start to avoid 416 errors
                ])
                veo_cmd.append(url)

                try:
                    result = subprocess.run(
                        veo_cmd,
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30 mins for 6GB+ files
                    )

                    actual_output = self._find_output_file(filename, result.stdout + result.stderr)
                    if actual_output and Path(actual_output).exists():
                        size_gb = os.path.getsize(actual_output) / (1024 ** 3)
                        logger.info(f"Veo download success ({quality}): {size_gb:.2f} GB Saved to {actual_output}")
                        return str(Path(actual_output).absolute())

                    if result.returncode != 0:
                        logger.warning(f"Format {quality} failed: {result.stderr[-200:].strip()}")

                except subprocess.TimeoutExpired:
                    logger.error(f"Download timed out for quality: {quality}")
                    continue

            return None
        except Exception as e:
            logger.exception(f"Critical error in _download_veo: {e}")
            return None

    async def download(self, url: str, filename: str, **kwargs) -> Optional[str]:
        if "app.veo.co" in url:
            return await self._download_veo(url, filename)
        # ... (rest of your existing platform detection logic)
        return None

    def _find_output_file(self, base_filename: str, ytdlp_output: str) -> Optional[str]:
        try:
            merge_pattern = r'Merging formats into "([^"]+\.(?:mp4|webm|mkv))"'
            merge_match = re.search(merge_pattern, ytdlp_output)
            if merge_match: return merge_match.group(1)

            dest_pattern = r'Destination:\s+([^\s]+\.(?:mp4|webm|mkv))'
            dest_matches = re.findall(dest_pattern, ytdlp_output)
            if dest_matches: return dest_matches[-1]

            for ext in ['.mp4', '.webm', '.mkv']:
                if Path(f"{base_filename}{ext}").exists(): return f"{base_filename}{ext}"
            return None
        except Exception:
            return None