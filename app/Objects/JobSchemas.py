import uuid
from datetime import datetime
from pydantic import BaseModel
from app.Infrastructure.Database import PydModel


class JobBaseSchema(PydModel):
    slug: str
    title: str
    description: str
    salary: str | None = None
    location: str | None = None
    employment_type: str | None = None
    tags: list[str] = []
    apply_url: str | None = None
    is_published: bool = True


class CreateJobRequest(JobBaseSchema):
    pass


class UpdateJobRequest(PydModel):
    slug: str | None = None
    title: str | None = None
    description: str | None = None
    salary: str | None = None
    location: str | None = None
    employment_type: str | None = None
    tags: list[str] | None = None
    apply_url: str | None = None
    is_published: bool | None = None


class JobResponse(JobBaseSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ListJobsResponse(BaseModel):
    items: list[JobResponse]
