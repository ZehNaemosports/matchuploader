import subprocess
from pathlib import Path
from typing import Optional
import os
import logging
import re
import requests

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
    ):
        self.preferred_quality = preferred_quality
        self.fallback_quality = "720"
        self.cookies_path = cookies_path
        self.facebook_cookies_path = facebook_cookies_path

    # --------------------------------------------------------
    # Platform detection
    # --------------------------------------------------------

    def _is_youtube(self, url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url

    def _is_veo(self, url: str) -> bool:
        return "veo.co" in url

    def _is_facebook(self, url: str) -> bool:
        return "facebook.com" in url

    def _is_pixellot(self, url: str) -> bool:
        return "pixellot" in url

    # --------------------------------------------------------
    # Pixellot extraction
    # --------------------------------------------------------

    def _extract_pixellot_m3u8(self, url: str) -> Optional[str]:

        try:
            logger.info("[PIXELLOT] Resolving stream...")

            session = requests.Session()

            response = session.get(
                url,
                timeout=10,
                allow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            final_url = response.url

            logger.info(f"[PIXELLOT] Final URL: {final_url}")

            response = session.get(
                final_url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            matches = re.findall(
                r"https://[^\s\"']+\.m3u8",
                response.text
            )

            if matches:
                logger.info(f"[PIXELLOT] Found stream: {matches[0]}")
                return matches[0]

            logger.error("[PIXELLOT] No m3u8 found in final page")
            return None

        except Exception as e:
            logger.exception(f"[PIXELLOT] Extraction error: {e}")
            return None

    # --------------------------------------------------------
    # Video validation
    # --------------------------------------------------------

    def _is_valid_video_file(self, path: str) -> bool:

        try:

            if not path:
                return False

            file_path = Path(path)

            if not file_path.exists():
                return False

            # reject image files
            invalid_exts = [".webp", ".jpg", ".jpeg", ".png"]

            if file_path.suffix.lower() in invalid_exts:
                logger.warning(f"Rejected non-video file: {path}")
                return False

            # reject tiny files
            size_mb = file_path.stat().st_size / (1024 * 1024)

            if size_mb < 2:
                logger.warning(
                    f"Rejected suspiciously small file ({size_mb:.2f} MB): {path}"
                )
                return False

            # verify actual video stream
            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=codec_type",
                    "-of", "csv=p=0",
                    path
                ],
                capture_output=True,
                text=True
            )

            has_video = "video" in probe.stdout.lower()

            if not has_video:
                logger.warning(f"No video stream found: {path}")

            return has_video

        except Exception as e:
            logger.warning(f"Video validation failed: {e}")
            return False

    # --------------------------------------------------------
    # Base yt-dlp command
    # --------------------------------------------------------

    def _build_base_command(self, use_tor=False, is_facebook=False):

        cmd = [
            "yt-dlp",

            "--no-playlist",
            "--newline",
            "--progress",

            "--retries", "50",
            "--fragment-retries", "50",
            "--extractor-retries", "10",

            "--socket-timeout", "30",

            "--continue",
            "--part",

            "--remote-components", "ejs:github",
        ]

        # cookies
        if (
            is_facebook
            and self.facebook_cookies_path
            and os.path.exists(self.facebook_cookies_path)
        ):
            cmd.extend([
                "--cookies",
                self.facebook_cookies_path
            ])

        elif self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend([
                "--cookies",
                self.cookies_path
            ])

        # facebook headers
        if is_facebook:
            cmd.extend([
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",

                "--referer",
                "https://www.facebook.com/"
            ])

        # YouTube via Tor
        if use_tor:
            cmd.extend([
                "--proxy",
                "socks5://127.0.0.1:9050",

                "--concurrent-fragments",
                "1",

                "--limit-rate",
                "9M",

                "--force-ipv4",

                "--youtube-skip-dash-manifest",
            ])

        else:
            cmd.extend([
                "--concurrent-fragments",
                "5"
            ])

        return cmd

    # --------------------------------------------------------
    # Main download
    # --------------------------------------------------------

    async def download(self, url: str, filename: str):

        try:

            is_youtube = self._is_youtube(url)
            is_veo = self._is_veo(url)
            is_facebook = self._is_facebook(url)
            is_pixellot = self._is_pixellot(url)

            # --------------------------------------------------------
            # Logging
            # --------------------------------------------------------

            if is_youtube:
                logger.info(f"[YOUTUBE] Downloading: {url} (via Tor)")

            elif is_veo:
                logger.info(f"[VEO] Downloading: {url}")

            elif is_pixellot:
                logger.info(f"[PIXELLOT] Downloading: {url}")

            elif is_facebook:
                logger.info(f"[FACEBOOK] Downloading: {url}")

            else:
                logger.info(f"[UNKNOWN SOURCE] Downloading: {url}")

            # --------------------------------------------------------
            # Pixellot handling
            # --------------------------------------------------------

            if is_pixellot:

                stream_url = self._extract_pixellot_m3u8(url)

                if not stream_url:
                    return None

                url = stream_url

            output_pattern = f"{filename}.%(ext)s"

            # --------------------------------------------------------
            # Quality attempts
            # --------------------------------------------------------

            if is_veo or is_pixellot:
                qualities_to_try = [None]

            else:
                qualities_to_try = [
                    self.preferred_quality,
                    self.fallback_quality,
                    None
                ]

            # --------------------------------------------------------
            # Download loop
            # --------------------------------------------------------

            for idx, quality in enumerate(qualities_to_try):

                use_tor = is_youtube

                cmd = self._build_base_command(
                    use_tor=use_tor,
                    is_facebook=is_facebook
                )

                # --------------------------------------------------------
                # Format selection
                # --------------------------------------------------------

                if is_veo:

                    format_spec = (
                        "bestvideo[height<=1080]"
                        "+bestaudio/"
                        "best[height<=1080]/best"
                    )

                elif is_pixellot:

                    format_spec = "best"

                else:

                    if quality:

                        format_spec = (
                            f"bestvideo[height<={quality}]"
                            f"+bestaudio/"
                            f"best[height<={quality}]/best"
                        )

                    else:

                        format_spec = (
                            "bestvideo+bestaudio/"
                            "best"
                        )

                cmd.extend([
                    "-f",
                    format_spec,

                    "--merge-output-format",
                    "mp4",

                    "-o",
                    output_pattern,

                    url
                ])

                logger.info(
                    f"RUNNING CMD (attempt {idx + 1}):\n{' '.join(cmd)}"
                )

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=7200 if use_tor else 1800
                )

                logger.info(result.stdout)

                if result.stderr:
                    logger.warning(result.stderr)

                # --------------------------------------------------------
                # Output detection
                # --------------------------------------------------------

                output_text = result.stdout + result.stderr

                actual_output = self._find_output_file(
                    filename,
                    output_text
                )

                possible_files = []

                if actual_output:
                    possible_files.append(actual_output)

                for ext in [
                    ".mp4",
                    ".mkv",
                    ".webm"
                ]:
                    possible_files.append(f"{filename}{ext}")

                # deduplicate
                possible_files = list(dict.fromkeys(possible_files))

                # validate
                for file_path in possible_files:

                    if self._is_valid_video_file(file_path):

                        logger.info(
                            f"Download success: {file_path}"
                        )

                        return str(
                            Path(file_path).absolute()
                        )

                logger.warning(
                    f"Download failed for quality {quality}, trying next..."
                )

            logger.error("All download attempts failed")
            return None

        except Exception as e:
            logger.exception(f"Download error: {e}")
            return None

    # --------------------------------------------------------
    # Detect output file
    # --------------------------------------------------------

    def _find_output_file(
        self,
        base_filename: str,
        ytdlp_output: str
    ):

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

            for ext in [
                ".mp4",
                ".webm",
                ".mkv"
            ]:

                candidate = f"{base_filename}{ext}"

                if Path(candidate).exists():
                    return candidate

            return None

        except Exception:
            return None