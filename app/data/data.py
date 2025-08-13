from .schema import Match
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

class Data:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database

    async def get_match(self, matchId: str) -> Match:
        match = await self.database.get_collection('mergedmatches').find_one({"_id": ObjectId(matchId)})
        print(match)
        match = Match(**match)
        return match

    async def update_match_video(self, matchId: str, videoUrl: str):
        await self.database.get_collection('mergedmatches').update_one({"_id": ObjectId(matchId)}, {"$set": {"match_video": videoUrl}})
        return True

    async def get_matches(self):
        matches_cursor = self.database.get_collection('mergedmatches').find().limit(10)
        print(matches_cursor)
        matches = await matches_cursor.to_list(length=10)
        print(matches)
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
                    },
                    "$or": [
                        {"hasHomeBeenClipped": {"$in": [None, False]}},
                        {"hasAwayBeenClipped": {"$in": [None, False]}}
                    ]
                },
                {
                    "_id": 1,
                    "match_video": 1,
                    "hasHomeBeenClipped": 1,
                    "hasAwayBeenClipped": 1
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
                "match_video": match.get("match_video", ""),
                "hasHomeBeenClipped": match.get("hasHomeBeenClipped"),
                "hasAwayBeenClipped": match.get("hasAwayBeenClipped"),
            })

        return results
