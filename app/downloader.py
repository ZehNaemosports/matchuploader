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
        use_remote_components: bool = True,  # NEW: Enable EJS by default
    ):
        self.preferred_quality = preferred_quality
        self.fallback_quality = '720'  # Fixed fallback quality
        self.cookies_path = cookies_path
        self.use_tor = use_tor
        self.use_remote_components = use_remote_components  # NEW

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
        """
        Base yt-dlp command used everywhere.
        This guarantees:
        - JS runtime
        - Cookies
        - Tor (if enabled)
        - Remote components for JS challenges
        """
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--js-runtimes", "deno",
        ]

        # Add remote components for JS challenge solving
        if self.use_remote_components:
            cmd.extend(["--remote-components", "ejs:github"])

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

    async def update_ytdlp(self):
        """Update yt-dlp to latest version"""
        try:
            logger.info("Updating yt-dlp...")
            
            # For pip installation
            update_cmd = ["pip", "install", "--upgrade", "yt-dlp"]
            
            result = subprocess.run(
                update_cmd,
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                logger.info("yt-dlp updated successfully")
                # Get new version
                version_result = subprocess.run(
                    ["yt-dlp", "--version"],
                    capture_output=True,
                    text=True,
                )
                if version_result.returncode == 0:
                    logger.info(f"Current version: {version_result.stdout.strip()}")
                return True
            else:
                logger.error(f"Failed to update yt-dlp: {result.stderr}")
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
            ]
            
            result = subprocess.run(
                update_cmd,
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                logger.info("Remote components updated successfully")
                return True
            else:
                logger.warning(f"Remote components update had issues: {result.stderr}")
                # Continue anyway - components might still work
                return True
                
        except Exception as e:
            logger.exception(f"Error updating components: {e}")
            return False

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

    async def download(self, url: str, filename: str, auto_update: bool = False) -> Optional[str]:
        """
        Download video with automatic updates if enabled
        
        Args:
            url: Video URL
            filename: Output filename (without extension)
            auto_update: If True, update yt-dlp and components before download
        """
        try:
            # Auto-update if requested
            if auto_update:
                await self.update_ytdlp()
                await self.update_components()

            # List available formats first for debugging
            await self.list_formats(url)

            # Use pattern for extension to avoid .mp4.webm issue
            output_path = f"{filename}.%(ext)s"

            # -------------------------
            # VEO HANDLING (NO TOR)
            # -------------------------
            if "app.veo.co" in url:
                veo_cmd = [
                    "yt-dlp",
                    "--no-playlist",
                    "--js-runtimes", "deno",
                ]

                # Add remote components for Veo too if enabled
                if self.use_remote_components:
                    veo_cmd.extend(["--remote-components", "ejs:github"])

                if self.cookies_path and os.path.exists(self.cookies_path):
                    veo_cmd.extend(["--cookies", self.cookies_path])

                veo_cmd.extend([
                    "-f", "standard-1080p",
                    "--merge-output-format", "mp4",
                    "-o", output_path,
                    "--no-check-certificate",
                    url,
                ])

                logger.info("Downloading Veo video (Tor disabled)")
                logger.info(f"Command: {' '.join(veo_cmd)}")

                result = subprocess.run(
                    veo_cmd,
                    capture_output=True,
                    text=True,
                )

                # Find actual output file (since we used %(ext)s pattern)
                actual_output = self._find_output_file(filename, result.stdout + result.stderr)
                if actual_output and Path(actual_output).exists():
                    size = os.path.getsize(actual_output) / (1024 * 1024)
                    logger.info(f"Veo download completed: {size:.2f} MB")
                    return str(Path(actual_output).absolute())

                logger.error(f"Veo download failed: {result.stderr}")
                return None

            # -------------------------
            # YOUTUBE DOWNLOAD - Try 1080p first, fallback to 720p
            # -------------------------
            
            # First attempt: Preferred quality (1080p)
            preferred_cmd = self._build_base_command() + [
                "-f", f"bestvideo[height<={self.preferred_quality}]+bestaudio/best[height<={self.preferred_quality}]",
                "--merge-output-format", "mp4",
                "-o", output_path,
                "--no-check-certificate",
                url,
            ]

            logger.info(f"Downloading YouTube video - Trying {self.preferred_quality}p first")
            logger.info(f"Output pattern: {output_path}")
            logger.info(f"Command: {' '.join(preferred_cmd)}")

            result = subprocess.run(
                preferred_cmd,
                capture_output=True,
                text=True,
            )

            # Find actual output file
            actual_output = self._find_output_file(filename, result.stdout + result.stderr)
            if actual_output and Path(actual_output).exists():
                size = os.path.getsize(actual_output) / (1024 * 1024)
                logger.info(f"YouTube download completed at {self.preferred_quality}p: {size:.2f} MB")
                return str(Path(actual_output).absolute())

            logger.warning(f"Preferred quality ({self.preferred_quality}p) download failed: {result.stderr}")
            
            # Remove any incomplete file
            if actual_output and Path(actual_output).exists():
                try:
                    os.remove(actual_output)
                    logger.info(f"Removed incomplete/corrupted file: {actual_output}")
                except Exception as e:
                    logger.warning(f"Could not remove file {actual_output}: {e}")

            # Second attempt: Fallback quality (720p)
            logger.info(f"Trying fallback quality: {self.fallback_quality}p")
            
            fallback_cmd = self._build_base_command() + [
                "-f", f"bestvideo[height<={self.fallback_quality}]+bestaudio/best[height<={self.fallback_quality}]",
                "--merge-output-format", "mp4",
                "-o", output_path,
                "--no-check-certificate",
                url,
            ]

            logger.info(f"Fallback command: {' '.join(fallback_cmd)}")

            fallback_result = subprocess.run(
                fallback_cmd,
                capture_output=True,
                text=True,
            )

            actual_output = self._find_output_file(filename, fallback_result.stdout + fallback_result.stderr)
            if actual_output and Path(actual_output).exists():
                size = os.path.getsize(actual_output) / (1024 * 1024)
                logger.info(f"Fallback download succeeded at {self.fallback_quality}p: {size:.2f} MB")
                return str(Path(actual_output).absolute())

            logger.error(f"Fallback quality ({self.fallback_quality}p) also failed")

            # -------------------------
            # LAST RESORT FALLBACK - Let yt-dlp choose any format
            # -------------------------
            logger.info("Trying last resort fallback (any format)")
            
            last_resort_cmd = self._build_base_command() + [
                "-o", output_path,
                url,
            ]

            logger.info(f"Last resort command: {' '.join(last_resort_cmd)}")

            last_resort_result = subprocess.run(
                last_resort_cmd,
                capture_output=True,
                text=True,
            )

            actual_output = self._find_output_file(filename, last_resort_result.stdout + last_resort_result.stderr)
            if actual_output and Path(actual_output).exists():
                size = os.path.getsize(actual_output) / (1024 * 1024)
                logger.info(f"Last resort fallback succeeded: {size:.2f} MB")
                return str(Path(actual_output).absolute())

            logger.error("All download attempts failed")
            return None

        except Exception as e:
            logger.exception(f"Critical error in download: {e}")
            return None

    def _find_output_file(self, base_filename: str, ytdlp_output: str) -> Optional[str]:
        """
        Extract the actual output filename from yt-dlp output
        since we use %(ext)s pattern
        """
        try:
            # Look for patterns like "Destination: filename.ext"
            import re
            patterns = [
                r'Destination:\s+([^\s]+\.(?:mp4|webm|mkv|avi|mov))',
                r'Merging formats into "([^"]+)"',
                r'\[download\]\s+([^\s]+\.(?:mp4|webm|mkv|avi|mov))\s+has already been downloaded',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, ytdlp_output)
                if matches:
                    return matches[-1]  # Return the last match (final output)
            
            # Fallback: Look for files with base_filename in current directory
            for ext in ['.mp4', '.webm', '.mkv', '.avi', '.mov']:
                possible = f"{base_filename}{ext}"
                if Path(possible).exists():
                    return possible
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not parse output filename: {e}")
            return None
