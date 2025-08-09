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
        if "app.veo.co" in url:
            try:
                subprocess.run(["yt-dlp", "--version"], check=True, capture_output=True)
                output_path = f"{filename}.mp4"
        
                cmd = [
                    "yt-dlp",
                    "-o", output_path,
                    "--merge-output-format", "mp4",
                    "--no-check-certificate",
                    url
                ]
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                print("Download completed successfully!")
                final_filename = f'{filename}.mp4'
                if Path(final_filename).exists():
                    return Path(final_filename).absolute()
                else:
                    print("Download failed:", result.stderr)
                    return None
                
            except subprocess.CalledProcessError as e:
                print(f"Error downloading video: {e.stderr}")
                return None
            except FileNotFoundError:
                print("yt-dlp not found. Please install it first.")
                return None
            
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
        
# s = YoutubeDownloader()
# print(s.download(url="https://app.veo.co/matches/20250727-ivory-coast-contre-makinde-fc-vs-kolia-fc-ligafci-a2d2c313/", filename="test"))