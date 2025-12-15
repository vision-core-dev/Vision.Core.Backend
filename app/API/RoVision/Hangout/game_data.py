from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobProgress(BaseModel):
    level: int = 1
    experience: int = 0


class Jobs(BaseModel):
    driver: JobProgress = JobProgress()
    conductor: JobProgress = JobProgress()
    passenger: JobProgress = JobProgress()


class HangoutUserData(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    rbx_user_id: int
    money: int = 0
    jobs: Jobs = Jobs()
    last_login_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)