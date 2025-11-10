from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.Objects.tasks.SubtaskModel import SubtaskBase


class UserPreview(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None


class TagPreview(BaseModel):
    id: uuid.UUID
    name: str
    color: str


class AttachmentPreview(BaseModel):
    id: uuid.UUID
    type: str
    url: str
    name: Optional[str] = None
    created_at: datetime | None = None


class CommentPreview(BaseModel):
    id: uuid.UUID
    user: UserPreview
    content: str
    created_at: datetime


class TaskDetailsResponse(BaseModel):
    id: uuid.UUID
    list_id: uuid.UUID
    name: str
    description: Optional[str]
    banner_url: Optional[str] = None
    tags: List[TagPreview]
    assignees: List[UserPreview]
    started_at: Optional[datetime]
    deadline_at: Optional[datetime]
    completed_at: Optional[datetime]
    attachments: List[AttachmentPreview]
    subtasks: List[SubtaskBase]
    comments: List[CommentPreview]
    created_by: UserPreview
    created_at: datetime
