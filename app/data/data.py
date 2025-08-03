from .schema import Match
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

class Data:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database

    async def get_match(self, matchId: str) -> Match:
        match = await self.database.get_collection('mergedmatches').find_one({"_id": ObjectId(matchId)})
        match = Match(**match)
        print(match)
        return match