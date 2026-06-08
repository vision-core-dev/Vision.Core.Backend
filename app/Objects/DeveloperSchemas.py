from pydantic import BaseModel
from app.Infrastructure.Database import PydModel
from app.Objects.DeveloperModel import DeveloperBase, DeveloperType, SocialLink


class DeveloperBaseSchema(PydModel):
    slug: str
    type: str = DeveloperType.STUDIO.value
    name: str
    tagline: str | None = None
    description: str | None = None
    role: str | None = None
    avatar_url: str | None = None
    logo_url: str | None = None
    founded_year: int | None = None
    location: str | None = None
    website: str | None = None
    parent_slug: str | None = None
    member_slugs: list[str] = []
    game_slugs: list[str] = []
    socials: list[SocialLink] = []
    is_published: bool = True
    sort_order: int = 0


class CreateDeveloperRequest(DeveloperBaseSchema):
    pass


class UpdateDeveloperRequest(PydModel):
    slug: str | None = None
    type: str | None = None
    name: str | None = None
    tagline: str | None = None
    description: str | None = None
    role: str | None = None
    avatar_url: str | None = None
    logo_url: str | None = None
    founded_year: int | None = None
    location: str | None = None
    website: str | None = None
    parent_slug: str | None = None
    member_slugs: list[str] | None = None
    game_slugs: list[str] | None = None
    socials: list[SocialLink] | None = None
    is_published: bool | None = None
    sort_order: int | None = None


class DeveloperResponse(DeveloperBase):
    pass


class ListDevelopersResponse(BaseModel):
    items: list[DeveloperResponse]
