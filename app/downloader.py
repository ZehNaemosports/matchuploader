import subprocess
from pathlib import Path
from typing import Optional

class YoutubeDownloader:
    def __init__(self, quality='720', cookies_path: Optional[str] = "/home/ubuntu/cookies.txt"):
        self.quality = quality
        self.cookies_path = cookies_path

    def set_quality(self, quality):
        self.quality = quality

    async def download(self, url: str, filename: str) -> Optional[str]:
        format_selector = f'bestvideo[height<={self.quality}]+bestaudio/best[height<={self.quality}]'

        cmd = [
            'yt-dlp',
            '-f', format_selector,
            '--merge-output-format', 'mp4',
            '--embed-thumbnail',
            '--embed-metadata',
            '--audio-quality', '0',
            '-o', f'{filename}.%(ext)s',
            '--no-simulate',
        ]

        if self.cookies_path:
            cmd += ['--cookies', self.cookies_path]

        cmd.append(url)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            final_filename = f'{filename}.mp4'
            if Path(final_filename).exists():
                return Path(final_filename).absolute()
            else:
                print("Download failed:", result.stderr)
                return None

        except FileNotFoundError:
            print("Error: yt-dlp not found. Please install yt-dlp first.")
            return None
