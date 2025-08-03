from datetime import datetime
from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field, BeforeValidator
from bson import ObjectId

def validate_objectid(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")

PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(validate_objectid)
]

class MatchBase(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
        "validate_by_name": True,
        "json_encoders": {ObjectId: str},
    }

class Match(MatchBase):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    old_away_match_id: Optional[PyObjectId] = Field(None, alias="oldAwayMatchId")
    match_video: Optional[str] = Field(None, alias="matchVideo")
    season_id: Optional[PyObjectId] = Field(None, alias="seasonId")
    competition_id: Optional[PyObjectId] = Field(None, alias="competitionId")

    home_team: PyObjectId = Field(..., alias="homeTeam")
    away_team: Optional[PyObjectId] = Field(None, alias="awayTeam")
    home_team_string: Optional[str] = Field(None, alias="homeTeamString")
    away_team_string: Optional[str] = Field(None, alias="awayTeamString")
    home_goals: Optional[int] = Field(None, alias="homeGoals")
    away_goals: Optional[int] = Field(None, alias="awayGoals")
    home_team_starting_direction: Optional[str] = Field(
        None, alias="homeTeamStartingDirection"
    )
    away_team_starting_direction: Optional[str] = Field(
        None, alias="awayTeamStartingDirection"
    )

    home_team_line_up: Optional[List[Dict[str, Any]]] = Field(
        None, alias="homeTeamLineUp"
    )
    away_team_line_up: Optional[List[Dict[str, Any]]] = Field(
        None, alias="awayTeamLineUp"
    )
    home_team_subs: Optional[List[Dict[str, Any]]] = Field(
        None, alias="homeTeamSubs"
    )
    away_team_subs: Optional[List[Dict[str, Any]]] = Field(
        None, alias="awayTeamSubs"
    )

    home_team_color: Optional[str] = Field(None, alias="homeTeamColor")
    away_team_color: Optional[str] = Field(None, alias="awayTeamColor")

    home_formation: Optional[str] = Field(None, alias="homeFormation")
    away_formation: Optional[str] = Field(None, alias="awayFormation")

    match_start_time: Optional[str] = Field(None, alias="matchStartTime")
    first_half_end_time: Optional[str] = Field(None, alias="firstHalfEndTime")
    second_half_start_time: Optional[str] = Field(None, alias="secondHalfStartTime")
    match_end_time: Optional[str] = Field(None, alias="matchEndTime")

    extra_time_match_start_time: Optional[str] = Field(
        None, alias="extraTimeMatchStartTime"
    )
    extra_time_first_half_end_time: Optional[str] = Field(
        None, alias="extraTimeFirstHalfEndTime"
    )
    extra_time_second_half_start_time: Optional[str] = Field(
        None, alias="extraTimeSecondHalfStartTime"
    )
    extra_time_match_end_time: Optional[str] = Field(
        None, alias="extraTimeMatchEndTime"
    )

    penalty_shoot_out_start_time: Optional[str] = Field(
        None, alias="penaltyShootOutStartTime"
    )
    penalty_shoot_out_end_time: Optional[str] = Field(
        None, alias="penaltyShootOutEndTime"
    )

    has_home_line_up: Optional[bool] = Field(None, alias="hasHomeLineUp")
    has_home_post_match_info: Optional[bool] = Field(None, alias="hasHomePostMatchInfo")
    has_away_line_up: Optional[bool] = Field(None, alias="hasAwayLineUp")
    has_away_post_match_info: Optional[bool] = Field(None, alias="hasAwayPostMatchInfo")
    has_video: Optional[bool] = Field(None, alias="hasVideo")
    match_type: Optional[int] = Field(None, alias="matchType")
    is_home_scheduled: Optional[bool] = Field(None, alias="isHomeScheduled")
    is_away_scheduled: Optional[bool] = Field(None, alias="isAwayScheduled")

    is_tagged_team_home: Optional[int] = Field(None, alias="isTaggedTeamHome")
    is_tagged_team_away: Optional[int] = Field(None, alias="isTaggedTeamAway")
    is_home_match_tagged: Optional[bool] = Field(None, alias="isHomeMatchTagged")
    is_away_match_tagged: Optional[bool] = Field(None, alias="isAwayMatchTagged")
    is_home_match_reviewed: Optional[bool] = Field(None, alias="isHomeMatchReviewed")
    is_away_match_reviewed: Optional[bool] = Field(None, alias="isAwayMatchReviewed")

    has_home_been_clipped: Optional[bool] = Field(None, alias="hasHomeBeenClipped")
    has_away_been_clipped: Optional[bool] = Field(None, alias="hasAwayBeenClipped")
    has_home_been_rated: Optional[bool] = Field(None, alias="hasHomeBeenRated")
    has_away_been_rated: Optional[bool] = Field(None, alias="hasAwayBeenRated")
    is_home_being_clipped: Optional[bool] = Field(None, alias="isHomeBeingClipped")
    is_away_being_clipped: Optional[bool] = Field(None, alias="isAwayBeingClipped")

    home_substitutions: Optional[List[Dict[str, Any]]] = Field(
        None, alias="homeSubstitutions"
    )
    away_substitutions: Optional[List[Dict[str, Any]]] = Field(
        None, alias="awaySubstitutions"
    )

    stadium: Optional[str] = None
    home_team_tagger_id: Optional[PyObjectId] = Field(None, alias="homeTeamTaggerId")
    away_team_tagger_id: Optional[PyObjectId] = Field(None, alias="awayTeamTaggerId")
    home_team_reviewer_id: Optional[PyObjectId] = Field(None, alias="homeTeamReviewerId")
    away_team_reviewer_id: Optional[PyObjectId] = Field(None, alias="awayTeamReviewerId")
    home_team_tag_date: Optional[datetime] = Field(None, alias="homeTeamTagDate")
    away_team_tag_date: Optional[datetime] = Field(None, alias="awayTeamTagDate")
    home_team_review_date: Optional[datetime] = Field(None, alias="homeTeamReviewDate")
    away_team_review_date: Optional[datetime] = Field(None, alias="awayTeamReviewDate")
    source: Optional[str] = None
    time: Optional[str] = None
    date: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

    model_config = {
        **MatchBase.model_config,
        "json_schema_extra": {
            "example": {
                "homeTeam": "507f1f77bcf86cd799439011",
                "awayTeam": "507f1f77bcf86cd799439012",
                "homeGoals": 2,
                "awayGoals": 1,
                "stadium": "Main Stadium",
                "matchStartTime": "15:00",
                "hasVideo": True
            }
        }
    }
