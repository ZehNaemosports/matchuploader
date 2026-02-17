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

class MergeVideosMessage(Message):
    command: str = "Merge_Video"
    video1: str = Field(..., alias="video1")
    video2: str = Field(..., alias="video2")
    output_name: str = Field(..., alias="output_name")

class MergeRequest(BaseModel):
    video1: str
    video2: str
    output_name: str
