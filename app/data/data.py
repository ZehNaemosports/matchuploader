from .schema import Match
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

class Data:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database

    async def get_match(self, matchId: str) -> Match:
        match = await self.database.get_collection('mergedmatches').find_one({"_id": ObjectId(matchId)})
        match = Match(**match)
        return match

    async def update_match_video(self, matchId: str, videoUrl: str):
        await self.database.get_collection('mergedmatches').update_one({"_id": ObjectId(matchId)}, {"$set": {"match_video": videoUrl}})
        return True

    async def get_matches(self):
        matches_cursor = self.database.get_collection('mergedmatches').find().limit(10)
        matches = await matches_cursor.to_list(length=10)
        return matches

    # async def get_latest_matches(self):
    #     cursor = self.database.get_collection('mergedmatches').find(
    #         {}, 
    #         {"_id": 1, "match_video": 1}
    #     ).sort("_id", -1).limit(200)
        
    #     latest_matches = await cursor.to_list(length=200)
        
    #     results = []
    #     for match in latest_matches:
    #         created_at = match['_id'].generation_time
    #         results.append({
    #             "_id": str(match['_id']),
    #             "created_at": created_at,
    #             "match_video": match.get("match_video", "")
    #         })
            
    #     return results

    async def get_latest_matches(self):
        cursor = (
            self.database.get_collection("mergedmatches")
            .find(
                {
                    "match_video": {
                        "$not": {
                            "$regex": "(media\\.naemoapp\\.com|s3\\.amazonaws\\.com)"
                        }
                    }
                },
                {
                    "_id": 1,
                    "match_video": 1
                }
            )
            .sort("_id", -1)
            .limit(200)
        )

        latest_matches = await cursor.to_list(length=200)

        results = []
        for match in latest_matches:
            created_at = match["_id"].generation_time
            results.append({
                "_id": str(match["_id"]),
                "created_at": created_at,
                "match_video": match.get("match_video", "")
            })

        return results


    async def matches_count(self):
        count = await self.database.get_collection("mergedmatches").count_documents({
            "match_video": {
                "$not": {
                    "$regex": "(media\\.naemoapp\\.com|s3\\.amazonaws\\.com)"
                }
            }
        })
        return count



    # async def list_all_match_events(self, matchId: str):
    #     matchEventsCursor = self.database.get_collection('mergedplayermatchevents').find({"match_id": ObjectId(matchId)})
    #     matchEventsList = await matchEventsCursor.to_list(length=None)

    # async def list_matches_without_events(self):
    #     events_collection = self.database.get_collection('mergedplayermatchevents')
    #     matches_collection = self.database.get_collection('mergedmatches')

    #     match_ids_with_events = await events_collection.distinct("match_id")

    #     matches_cursor = matches_collection.find(
    #         {"_id": {"$nin": match_ids_with_events}},
    #         {"_id": 1}
    #     )

    #     match_ids_without_events = [match["_id"] async for match in matches_cursor]
    #     return match_ids_without_events
