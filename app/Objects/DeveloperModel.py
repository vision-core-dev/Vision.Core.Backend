import enum
import uuid
from datetime import datetime
from pydantic import field_validator
from sqlalchemy import Column, String, DateTime, UUID, TEXT, Boolean, Integer, JSON, ARRAY, func
from app.Infrastructure.Database import Base, PydModel


class DeveloperType(enum.Enum):
    STUDIO = "studio"
    PERSON = "person"


class Developer(Base):
    __tablename__ = "Developers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    slug = Column(String(100), nullable=False, unique=True, index=True)
    type = Column(String(20), nullable=False, server_default=DeveloperType.STUDIO.value)

    name = Column(String(200), nullable=False)
    tagline = Column(TEXT, nullable=True)
    description = Column(TEXT, nullable=True)

    # Person-only fields (no DB constraint; ignored on studios).
    role = Column(String(200), nullable=True)
    avatar_url = Column(TEXT, nullable=True)

    # Studio-only fields (no DB constraint; ignored on persons).
    logo_url = Column(TEXT, nullable=True)
    founded_year = Column(Integer, nullable=True)
    location = Column(String(200), nullable=True)
    website = Column(TEXT, nullable=True)

    # Soft refs (slugs of other developers). No DB FKs so slugs can be renamed freely.
    parent_slug = Column(String(100), nullable=True, index=True)
    member_slugs = Column(ARRAY(TEXT), nullable=True, default=list)
    # If null/empty, the frontend falls back to auto-matching by Games.developer_slug.
    game_slugs = Column(ARRAY(TEXT), nullable=True, default=list)

    # Social links — list of {"platform": str, "label": str, "href": str}.
    # `platform` is matched on the frontend to pick an icon (telegram, discord, github, ...).
    socials = Column(JSON, nullable=True, default=list)

    is_published = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SocialLink(PydModel):
    platform: str
    label: str
    href: str


class DeveloperBase(PydModel):
    id: uuid.UUID
    slug: str
    type: str
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
    created_at: datetime
    updated_at: datetime

    # DB columns are nullable; coerce NULL → [] so the JSON contract stays array-only.
    @field_validator("member_slugs", "game_slugs", "socials", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return [] if v is None else v
