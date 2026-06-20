from pydantic import BaseModel
from app.Infrastructure.Database import PydModel
from app.Objects.GameFeedPostModel import GameFeedPostWithAuthor


class GameFeedPostBaseSchema(PydModel):
    title: str | None = None
    content: str
    is_published: bool = True
    developer_slug: str | None = None


class CreateGameFeedPostRequest(GameFeedPostBaseSchema):
    pass


class UpdateGameFeedPostRequest(PydModel):
    title: str | None = None
    content: str | None = None
    is_published: bool | None = None
    developer_slug: str | None = None


class GameFeedPostResponse(GameFeedPostWithAuthor):
    pass


class ListGameFeedPostsResponse(BaseModel):
    items: list[GameFeedPostResponse]
