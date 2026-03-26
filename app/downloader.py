import subprocess
from pathlib import Path
from typing import Optional
import os
import logging
import re
import time

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
        use_tor: bool = False
    ):
        self.preferred_quality = preferred_quality
        self.fallback_quality = "720"
        self.cookies_path = cookies_path
        self.facebook_cookies_path = facebook_cookies_path
        self.use_tor = use_tor

    # --------------------------------------------------------
    # Base yt-dlp command (Tor-aware)
    # --------------------------------------------------------
    def _build_base_command(self, is_facebook=False):

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--newline",
            "--progress",

            # high resilience
            "--retries", "50",
            "--fragment-retries", "50",
            "--socket-timeout", "30",

            # resume support
            "--continue",
            "--part",

            # challenge solver
            "--remote-components", "ejs:github",
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

        # Tor proxy
        if self.use_tor:
            cmd.extend([
                "--proxy", "socks5://127.0.0.1:9050",
                "--concurrent-fragments", "1",
                "--limit-rate", "600K",
                "--force-ipv4",
            ])
        else:
            # non-Tor: faster
            cmd.extend([
                "--concurrent-fragments", "5"
            ])

        return cmd

    # --------------------------------------------------------
    # Main download
    # --------------------------------------------------------
    async def download(self, url: str, filename: str):

        try:
            logger.info(f"[YOUTUBE] Downloading: {url}")

            output_pattern = f"{filename}.%(ext)s"

            qualities_to_try = [
                self.preferred_quality,
                self.fallback_quality,
                None
            ]

            for quality in qualities_to_try:

                # retry attempts per quality
                for attempt in range(3):

                    cmd = self._build_base_command()

                    if quality:
                        format_spec = f"bv*[height<={quality}][tbr<2500]+ba/b[height<={quality}]"
                    else:
                        format_spec = "bv*[tbr<2500]+ba/b"

                    cmd.extend([
                        "-f", format_spec,
                        "--merge-output-format", "mp4",
                        "-o", output_pattern,
                        url
                    ])

                    logger.info(f"RUNNING CMD (attempt {attempt+1}):\n{' '.join(cmd)}")

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=7200 if self.use_tor else 1800  # long timeout for Tor
                    )

                    logger.info(result.stdout)

                    if result.stderr:
                        logger.warning(result.stderr)

                    output_text = result.stdout + result.stderr
                    actual_output = self._find_output_file(filename, output_text)

                    if actual_output and Path(actual_output).exists():
                        logger.info(f"Download success: {actual_output}")
                        return str(Path(actual_output).absolute())

                    logger.warning(f"Attempt {attempt+1} failed, retrying...")
                    time.sleep(10 if self.use_tor else 3)

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