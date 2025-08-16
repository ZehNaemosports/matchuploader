

import os
from pathlib import Path
from app.queue.sqs_client import SqsClient
from app.service.matchdownloader import MatchDownloader
import logging
import asyncio

logger = logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MessageProcessor:
    def __init__(self, sqs_client:  SqsClient, match_downloader: MatchDownloader):
        self.sqs_client = sqs_client
        self.match_downloader = match_downloader

    async def process_message(self, message_body: dict, receipt_handle: str):
        command = message_body.get("command")
        if command == "Match_Upload":
            match_id = message_body.get("matchId")
            
            if match_id:
                try:
                    video_path = await self.match_downloader.download_match_video(match_id)
                    if video_path:
                        object_key = os.path.basename(video_path)
                        upload_url = await self.match_downloader.upload_match_video(str(video_path), object_key)
                        if upload_url:
                            await self.match_downloader.data.update_match_video(match_id, upload_url)
                            logger.info(f"Successfully processed and uploaded match {match_id}. URL: {upload_url}")
                            self.sqs_client.delete_message(receipt_handle)
                            Path(video_path).unlink(missing_ok=True)
                        else:
                            logger.info(f"Failed to upload video for match {match_id}")
                    else:
                        logger.info(f"Failed to download video for match {match_id}")
                except Exception as e:
                    logger.info(f"Error processing Match_Upload for {match_id}: {e}")
                    self.sqs_client.delete_message(receipt_handle)
            else:
                logger.info("Match_Upload message missing matchId.")
        else:
            logger.info(f"Unknown command: {command}")

    async def poll_messages(self):
        logger.info("Starting message polling...")
        while True:
            response = self.sqs_client.receive_message()
            messages = response.get("Messages", [])

            if len(messages)>0:
                for msg in messages:
                    body = msg.get("Body")
                    receipt_handle = msg.get("ReceiptHandle")
                    try:
                        import json
                        message_body = json.loads(body)
                        await self.process_message(message_body, receipt_handle)
                    except Exception as e:
                        logger.info(f"Failed to process message: {e}")
            else:
                logger.info("No messages received.")

            logger.info('Sleeping for 15 minutes...')
            await asyncio.sleep(900)
            
