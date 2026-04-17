import uuid
from datetime import datetime
from pydantic import BaseModel
from app.Infrastructure.Database import PydModel
from app.Objects.UserModel import UserShort


class BlogPostBaseSchema(PydModel):
    slug: str
    title: str
    summary: str | None = None
    content: str
    thumbnail_url: str | None = None
    category: str | None = None
    tags: list[str] = []
    reading_time: str | None = None
    is_anonymous: bool = False
    is_published: bool = True
    published_at: datetime | None = None


class CreateBlogPostRequest(BlogPostBaseSchema):
    pass


class UpdateBlogPostRequest(PydModel):
    slug: str | None = None
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    thumbnail_url: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    reading_time: str | None = None
    is_anonymous: bool | None = None
    is_published: bool | None = None
    published_at: datetime | None = None


class BlogPostResponse(BlogPostBaseSchema):
    id: uuid.UUID
    author_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    author: UserShort | None = None


class ListBlogPostsResponse(BaseModel):
    items: list[BlogPostResponse]
