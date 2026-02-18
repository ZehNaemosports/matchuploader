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

        # Auto-update components on init if enabled
        if auto_update_components:
            self._update_components_sync()

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

    def _update_components_sync(self):
        """Synchronous component update (called from __init__)"""
        try:
            logger.info("Updating EJS components...")
            cmd = [
                "yt-dlp",
                "--remote-components", "ejs:github",
                "--update",
                "--quiet",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("EJS components updated successfully")
            else:
                logger.warning(f"EJS components update had issues: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            logger.warning("EJS components update timed out")
        except Exception as e:
            logger.warning(f"Could not update EJS components: {e}")

    def _build_base_command(self, include_components: bool = True, is_facebook: bool = False):
        """
        Base yt-dlp command with platform-specific options.
        """
        cmd = [
            "yt-dlp",
            "--no-playlist",
        ]

        # Add JavaScript runtime (for sites that need it)
        if not is_facebook:  # Facebook doesn't need JS runtime
            cmd.extend(["--js-runtimes", "deno"])

        # Add remote components if enabled and not Facebook
        if self.use_remote_components and include_components and not is_facebook:
            cmd.extend(["--remote-components", "ejs:github"])

        # Platform-specific cookie handling
        if is_facebook and self.facebook_cookies_path and os.path.exists(self.facebook_cookies_path):
            cmd.extend(["--cookies", self.facebook_cookies_path])
            logger.info("Using Facebook cookies")
        elif self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(["--cookies", self.cookies_path])
            logger.info("Using general cookies")

        # Facebook-specific headers
        if is_facebook:
            cmd.extend([
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--referer", "https://www.facebook.com/",
                "--add-header", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            ])

        if self.use_tor:
            cmd.extend([
                "--proxy", "socks5://localhost:9050",
                "--socket-timeout", "60",
                "--retries", "10",
                "--force-ipv4",
            ])

        return cmd

    def _get_facebook_formats(self, url: str):
        """Get available formats for Facebook video"""
        try:
            cmd = self._build_base_command(is_facebook=True) + ["-F", url]

            logger.info(f"Getting Facebook formats for: {url}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return self._parse_facebook_formats(result.stdout)
            else:
                logger.error(f"Failed to get Facebook formats: {result.stderr[:500]}")
                return None

        except Exception as e:
            logger.exception(f"Error getting Facebook formats: {e}")
            return None

    def _parse_facebook_formats(self, format_output: str) -> Dict[str, Any]:
        """Parse Facebook format output to extract available qualities"""
        formats = {
            '1080': {'video_id': None, 'audio_id': None},
            '720': {'video_id': None, 'audio_id': None},
            '360': {'video_id': None, 'audio_id': None},
            'audio': {'id': None},
        }

        try:
            lines = format_output.split('\n')
            for line in lines:
                # Look for video formats
                if 'mp4' in line and 'video only' in line:
                    # Parse resolution
                    res_match = re.search(r'(\d+)x(\d+)', line)
                    if res_match:
                        height = int(res_match.group(2))
                        # Extract format ID (first column)
                        parts = line.split()
                        if parts and parts[0].endswith('v'):
                            format_id = parts[0]

                            if height >= 1080:
                                formats['1080']['video_id'] = format_id
                            elif height >= 720:
                                formats['720']['video_id'] = format_id
                            elif height >= 360:
                                formats['360']['video_id'] = format_id

                # Look for audio format
                elif 'audio only' in line and 'm4a' in line:
                    parts = line.split()
                    if parts and parts[0].endswith('a'):
                        formats['audio']['id'] = parts[0]

            logger.info(f"Parsed Facebook formats: {formats}")
            return formats

        except Exception as e:
            logger.warning(f"Could not parse Facebook formats: {e}")
            return formats

    async def update_ytdlp(self):
        """Update yt-dlp to latest version"""
        try:
            logger.info("Updating yt-dlp...")

            update_cmd = ["pip", "install", "--upgrade", "yt-dlp"]

            result = subprocess.run(
                update_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                logger.info("yt-dlp updated successfully")
                version_result = subprocess.run(
                    ["yt-dlp", "--version"],
                    capture_output=True,
                    text=True,
                )
                if version_result.returncode == 0:
                    logger.info(f"Current version: {version_result.stdout.strip()}")
                return True
            else:
                logger.error(f"Failed to update yt-dlp: {result.stderr[:500]}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("yt-dlp update timed out")
            return False
        except Exception as e:
            logger.exception(f"Error updating yt-dlp: {e}")
            return False

    async def update_components(self):
        """Update remote components (EJS)"""
        try:
            logger.info("Updating remote components...")

            update_cmd = [
                "yt-dlp",
                "--remote-components", "ejs:github",
                "--update",
                "--quiet",
            ]

            result = subprocess.run(
                update_cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                logger.info("Remote components updated successfully")
                return True
            else:
                logger.warning(f"Remote components update had issues: {result.stderr[:200]}")
                return True  # Continue anyway

        except subprocess.TimeoutExpired:
            logger.warning("Remote components update timed out")
            return True
        except Exception as e:
            logger.exception(f"Error updating components: {e}")
            return False

    async def list_formats(self, url: str):
        """List available formats with timeout"""
        try:
            is_facebook = 'facebook.com' in url
            cmd = self._build_base_command(is_facebook=is_facebook) + ["-F", url]

            logger.info(f"Listing available formats for: {url}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # Add timeout
            )

            if result.returncode == 0:
                logger.debug(f"Available formats:\n{result.stdout}")
                return result.stdout
            else:
                logger.error(f"Failed to list formats: {result.stderr[:500]}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("Format listing timed out")
            return None
        except Exception as e:
            logger.exception(f"Error listing formats: {e}")
            return None

    async def download(self, url: str, filename: str, auto_update: bool = False,
                       max_attempts: int = 3, timeout_per_attempt: int = 300) -> Optional[str]:
        """
        Download video with improved fallback logic
        """
        try:
            # Auto-update if requested
            if auto_update:
                await self.update_ytdlp()
                await self.update_components()

            # Use pattern for extension
            output_pattern = f"{filename}.%(ext)s"

            # -------------------------
            # PLATFORM DETECTION
            # -------------------------
            if "facebook.com" in url:
                return await self._download_facebook(url, filename, timeout_per_attempt)
            elif "app.veo.co" in url:
                return await self._download_veo(url, filename)

            # -------------------------
            # YOUTUBE/GENERIC DOWNLOAD
            # -------------------------

            # First, get available formats to choose best one
            formats_info = await self.list_formats(url)

            # Try multiple quality attempts
            qualities_to_try = [
                (self.preferred_quality, "preferred"),
                (self.fallback_quality, "fallback"),
                (None, "any")  # Last resort: any quality
            ]

            for quality, attempt_name in qualities_to_try:
                logger.info(f"Attempting download: {attempt_name} ({quality}p if applicable)")

                cmd = self._build_base_command(is_facebook=False)

                if quality:  # Specific quality requested
                    # Use more reliable format selection
                    format_spec = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best[height<={quality}]"
                    cmd.extend([
                        "-f", format_spec,
                        "--merge-output-format", "mp4",
                    ])
                else:  # Any quality
                    cmd.extend([
                        "-f", "bestvideo+bestaudio/best",
                        "--merge-output-format", "mp4",
                    ])

                cmd.extend([
                    "-o", output_pattern,
                    "--no-check-certificate",
                    "--socket-timeout", str(timeout_per_attempt),
                    url,
                ])

                logger.debug(f"Command: {' '.join(cmd)}")

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout_per_attempt,
                    )

                    # Find actual output file
                    actual_output = self._find_output_file(filename, result.stdout + result.stderr)

                    if actual_output and Path(actual_output).exists():
                        size = os.path.getsize(actual_output) / (1024 * 1024)
                        logger.info(f"Download succeeded at {attempt_name} quality: {size:.2f} MB")
                        return str(Path(actual_output).absolute())

                    if result.returncode != 0:
                        logger.warning(f"Download attempt failed ({attempt_name}): {result.stderr[:500]}")

                    # Clean up any partial files
                    if actual_output and Path(actual_output).exists():
                        try:
                            os.remove(actual_output)
                            logger.debug(f"Removed incomplete file: {actual_output}")
                        except:
                            pass

                except subprocess.TimeoutExpired:
                    logger.warning(f"Download attempt timed out ({attempt_name})")
                    continue

            logger.error("All download attempts failed")
            return None

        except Exception as e:
            logger.exception(f"Critical error in download: {e}")
            return None

    async def _download_facebook(self, url: str, filename: str, timeout: int) -> Optional[str]:
        """Handle Facebook video downloads with quality fallback"""
        try:
            output_pattern = f"{filename}.%(ext)s"

            # Get available formats
            formats = self._get_facebook_formats(url)
            if not formats:
                logger.error("Could not get Facebook formats")
                return None

            # Try qualities in order: 1080p -> 720p -> 360p
            qualities_to_try = [
                ('1080', 'preferred 1080p'),
                ('720', 'fallback 720p'),
                ('360', 'fallback 360p'),
            ]

            for quality_key, attempt_name in qualities_to_try:
                video_id = formats.get(quality_key, {}).get('video_id')
                audio_id = formats.get('audio', {}).get('id')

                if not video_id or not audio_id:
                    logger.warning(f"{quality_key}p format not available, trying next...")
                    continue

                logger.info(f"Attempting Facebook download: {attempt_name}")

                # Build Facebook-specific command
                cmd = self._build_base_command(is_facebook=True)
                cmd.extend([
                    "-f", f"{video_id}+{audio_id}",
                    "--merge-output-format", "mp4",
                    "-o", output_pattern,
                    "--socket-timeout", str(timeout),
                    url,
                ])

                logger.debug(f"Facebook command: {' '.join(cmd)}")

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )

                    # Find actual output file
                    actual_output = self._find_output_file(filename, result.stdout + result.stderr)

                    if actual_output and Path(actual_output).exists():
                        size = os.path.getsize(actual_output) / (1024 * 1024)
                        logger.info(f"Facebook download succeeded at {quality_key}p: {size:.2f} MB")
                        return str(Path(actual_output).absolute())

                    if result.returncode != 0:
                        logger.warning(f"Facebook download attempt failed ({attempt_name}): {result.stderr[:500]}")

                except subprocess.TimeoutExpired:
                    logger.warning(f"Facebook download timed out ({attempt_name})")
                    continue

            logger.error("All Facebook download attempts failed")
            return None

        except Exception as e:
            logger.exception(f"Error downloading Facebook video: {e}")
            return None

    async def _download_veo(self, url: str, filename: str) -> Optional[str]:
        """Handle Veo video downloads with quality fallback and 416 error handling"""
        try:
            output_pattern = f"{filename}.%(ext)s"

            # Quality priority for Veo
            veo_qualities = ["standard-1080p", "standard-720p", "standard-480p", "best"]

            for quality in veo_qualities:
                logger.info(f"Attempting Veo download with quality: {quality}")

                veo_cmd = self._build_base_command(include_components=False, is_facebook=False)
                veo_cmd.extend([
                    "-f", quality,
                    "--merge-output-format", "mp4",
                    "-o", output_pattern,
                    "--no-check-certificate",
                    "--no-continue",  # Prevents 416 errors by starting fresh for each quality attempt
                    url,
                ])

                try:
                    result = subprocess.run(
                        veo_cmd,
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )

                    actual_output = self._find_output_file(filename, result.stdout + result.stderr)
                    if actual_output and Path(actual_output).exists():
                        size = os.path.getsize(actual_output) / (1024 * 1024)
                        logger.info(f"Veo download completed ({quality}): {size:.2f} MB")
                        return str(Path(actual_output).absolute())

                    logger.warning(f"Veo quality {quality} failed or unavailable, trying next fallback...")
                    if result.returncode != 0:
                        logger.debug(f"Veo error details: {result.stderr[:200]}")

                except subprocess.TimeoutExpired:
                    logger.warning(f"Veo download timed out for quality: {quality}")
                    continue

            logger.error("All Veo download attempts (1080p, 720p, 480p, best) failed")
            return None

        except Exception as e:
            logger.exception(f"Critical error downloading Veo video: {e}")
            return None

    def _find_output_file(self, base_filename: str, ytdlp_output: str) -> Optional[str]:
        """
        Extract the actual output filename from yt-dlp output
        """
        try:
            # Pattern for final merged file
            merge_pattern = r'Merging formats into "([^"]+\.(?:mp4|webm|mkv|avi|mov))"'
            merge_match = re.search(merge_pattern, ytdlp_output)
            if merge_match:
                return merge_match.group(1)

            # Pattern for destination files
            dest_pattern = r'Destination:\s+([^\s]+\.(?:mp4|webm|mkv|avi|mov))'
            dest_matches = re.findall(dest_pattern, ytdlp_output)
            if dest_matches:
                # Take the last one (likely the merged file)
                return dest_matches[-1]

            # Fallback: Look for files with base_filename in current directory
            for ext in ['.mp4', '.webm', '.mkv', '.avi', '.mov']:
                possible = f"{base_filename}{ext}"
                if Path(possible).exists():
                    return possible
                # Also try with different case
                possible_lower = f"{base_filename.lower()}{ext}"
                if Path(possible_lower).exists():
                    return possible_lower

            return None

        except Exception as e:
            logger.warning(f"Could not parse output filename: {e}")
            return None