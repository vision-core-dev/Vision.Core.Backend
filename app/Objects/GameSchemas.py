from pydantic import BaseModel
from app.Infrastructure.Database import PydModel
from app.Objects.GameModel import GameBase, GameStatus

class GameBaseSchema(PydModel):
    slug: str
    title: str
    summary: str | None = None
    content: str
    thumbnail_url: str | None = None
    play_url: str | None = None
    status: str = GameStatus.IN_DEVELOPMENT.value
    is_published: bool = True
    developer_slug: str | None = None

class CreateGameRequest(GameBaseSchema):
    pass

class UpdateGameRequest(PydModel):
    slug: str | None = None
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    thumbnail_url: str | None = None
    play_url: str | None = None
    status: str | None = None
    is_published: bool | None = None
    developer_slug: str | None = None

class GameResponse(GameBase):
    pass

class ListGamesResponse(BaseModel):
    items: list[GameResponse]
