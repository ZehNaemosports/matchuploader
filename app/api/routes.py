from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import FileResponse
import os
from app.dependencies import get_match_downloader, get_queue_client
from app.queue.redis_client import RedisQueueClient
from app.service.matchdownloader import MatchDownloader
from app.queue.messages import MatchUploadMessage, MergeVideosMessage, MergeRequest, DownloadVideoMessage
import json

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
        return {"message": "Match video uploaded successfully.", "url": result}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"An error occurred: {e}")

@router.post('/match/{matchId}/upload')
async def upload_match_video(matchId: str, queue_client: RedisQueueClient = Depends(get_queue_client) ):
    message = MatchUploadMessage(matchId=matchId)
    message.set_post_date()
    message_body_json = json.dumps(message.to_dict())
    response = queue_client.send_message(message_body_json)
    return response.get('MessageId')


@router.post('/merge_videos')
async def merge_videos(
        request: MergeRequest,
        queue_client: RedisQueueClient = Depends(get_queue_client)
):
    message = MergeVideosMessage(video1=request.video1, video2=request.video2, output_name=request.output_name)
    message.set_post_date()

    message_body_json = json.dumps(message.to_dict())
    response = queue_client.send_message(message_body_json)

    return response.get('MessageId')

@router.post("/download_video")
async def download_video(
        request: DownloadVideoMessage,
        queue_client: RedisQueueClient = Depends(get_queue_client)
):
    message = DownloadVideoMessage(link=request.link, output_name=request.output_name)
    message.set_post_date()
    message_body_json = json.dumps(message.to_dict())
    response = queue_client.send_message(message_body_json)
    return response.get('MessageId')
