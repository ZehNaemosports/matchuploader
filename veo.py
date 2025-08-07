import subprocess
import sys

def download_veo_video(url, output_path="veo_video.mp4"):
    """
    Download a Veo video using yt-dlp via subprocess
    
    Args:
        url (str): The Veo video URL
        output_path (str): Path to save the video
    """
    try:
        subprocess.run(["yt-dlp", "--version"], check=True, capture_output=True)
        
        cmd = [
            "yt-dlp",
            "-o", output_path,
            "--merge-output-format", "mp4",
            "--no-check-certificate",
            url
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Download completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error downloading video: {e.stderr}")
        return False
    except FileNotFoundError:
        print("yt-dlp not found. Please install it first.")
        return False

# Example usage
# veo_url = "https://app.veo.co/matches/20250716-ajamaat-fc-vs-fc-bignona-31295f86/"
# download_veo_video(veo_url, "ajamaat_vs_bignona.mp4")