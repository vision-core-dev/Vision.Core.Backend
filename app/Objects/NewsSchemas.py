import uuid
from datetime import datetime
from pydantic import BaseModel
from app.Infrastructure.Database import PydModel
from app.Objects.UserModel import UserShort

class NewsBaseSchema(PydModel):
    title: str | None = None
    content: str
    labels: list[str] = []
    target_text: str | None = None
    target_url: str | None = None

class CreateNewsRequest(NewsBaseSchema):
    pass

class UpdateNewsRequest(NewsBaseSchema):
    pass

class NewsResponse(NewsBaseSchema):
    id: uuid.UUID
    author_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    author: UserShort

class ListNewsResponse(BaseModel):
    items: list[NewsResponse]
