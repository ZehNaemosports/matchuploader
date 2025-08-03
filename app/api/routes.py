from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import FileResponse
import os
from app.data.data import Data
from app.dependencies import get_data, get_match_downloader
from app.service.matchdownloader import MatchDownloader

router = APIRouter()

@router.get("/matches/{match_id}/download", description="Downloads the video for a specific match.")
async def download_match_video_route(
    match_id: str,
    match_downloader: MatchDownloader = Depends(get_match_downloader)
):
    try:
        video_path = await match_downloader.download_match_video(match_id)
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Match video not found.")

        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=f"match_{match_id}.mp4"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while processing the download.")
    
@router.post("/matches/{match_id}/upload", description="Uploads the video for a specific match.")
async def upload_match_video_route(
    match_id: str,
    match_downloader: MatchDownloader = Depends(get_match_downloader)
):
    try:
        video_path = await match_downloader.download_match_video(match_id)
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Match video not found.")
        
        result = await match_downloader.upload_match_video(video_path, os.path.basename(video_path))
        if not result:
            raise HTTPException(status_code=500, detail="Failed to upload match video.")
        return {"message": "Match video uploaded successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"An error occurred: {e}")
        
        

    
# @router.get("/matches/{match_id}")
# async def get_match_route(
#     match_id: str,
#     data: Data = Depends(get_data)
# ):
#     try:
#         match = await data.get_match(match_id)
#         if not match:
#             raise HTTPException(status_code=404, detail="Match not found.")
#         return match
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error while processing the request.")


