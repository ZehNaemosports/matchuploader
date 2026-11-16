import json
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import Settings
from app.data.data import Data
from app.queue.redis_client import RedisQueueClient
import asyncio
from app.queue.messages import MatchUploadMessage
import pandas as pd

async def run():
    settings = Settings()

    queue_client = RedisQueueClient(
        redis_url=settings.redis_url,
        queue_name=settings.redis_queue_name,
    )

    mongodb_client = AsyncIOMotorClient(settings.database_connection_string)
    mongodb = mongodb_client[settings.database_name]
    data_service = Data(database=mongodb)

    matches = await data_service.get_latest_matches()
    matches = [m for m in matches if "media.naemoapp.com" not in m["match_video"]]
    for match in matches:
        if match.get("match_video") != "" and match.get("match_video") is not None:
            message = MatchUploadMessage(
                matchId=match["_id"],
                postDate=match["created_at"]
            )
            print(message)
            message.set_post_date()
            message_body_json = json.dumps(message.to_dict())
            response = queue_client.send_message(message_body_json)
            print(response)

    df  = pd.DataFrame(matches)
    df.to_csv("match_test.csv")
    

if __name__ == "__main__":
    asyncio.run(run())

