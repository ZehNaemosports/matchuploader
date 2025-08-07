from pydantic import BaseModel, Field
from datetime import datetime

class Message(BaseModel):
    command: str

    def set_post_date(self):
        return datetime.now()
    
    def to_dict(self):
        return self.model_dump()


class MatchUploadMessage(Message):
    command: str = "Match_Upload"
    matchId: str = Field(..., alias="matchId")
