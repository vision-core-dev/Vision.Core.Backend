from datetime import datetime
from typing import Optional, Dict

from pydantic import BaseModel, Field


class JobProgress(BaseModel):
    level: int = 1
    experience: int = 0


class Jobs(BaseModel):
    driver: JobProgress = JobProgress()
    conductor: JobProgress = JobProgress()
    passenger: JobProgress = JobProgress()


class StampData(BaseModel):
    page: int
    x: int
    y: int


class HangoutUserData(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    rbx_user_id: int

    playtime: int = 0
    long_session: int = 0
    driven_distance: int = 0
    money: int = 0

    jobs: Jobs = Jobs()

    stamps: Dict[str, StampData] = Field(default_factory=dict)

    last_login_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
