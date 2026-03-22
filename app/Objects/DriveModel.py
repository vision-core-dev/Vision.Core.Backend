import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, UUID, func, ARRAY, ForeignKey, Boolean, BigInteger, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base, PydModel


class DriveAccessType(enum.Enum):
    private = "private"       # only owner
    role = "role"             # specific roles
    public = "public"         # all users


class DriveFolder(Base):
    __tablename__ = "DriveFolders"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("DriveFolders.id", ondelete="CASCADE"), nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"), nullable=False)

    access_type = Column(ENUM(DriveAccessType, name="driveaccesstype", create_type=True), nullable=False, server_default="public")
    allowed_role_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True, default=[])

    is_task_disk = Column(Boolean, nullable=False, server_default="false")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=datetime.now())

    owner = relationship("User", foreign_keys=[owner_id])
    parent = relationship("DriveFolder", remote_side="DriveFolder.id", foreign_keys=[parent_id], back_populates="children")
    children = relationship("DriveFolder", foreign_keys=[parent_id], cascade="all, delete-orphan", back_populates="parent")
    files = relationship("DriveFile", back_populates="folder", cascade="all, delete-orphan")


class DriveFile(Base):
    __tablename__ = "DriveFiles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    folder_id = Column(UUID(as_uuid=True), ForeignKey("DriveFolders.id", ondelete="CASCADE"), nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(512), nullable=False)
    url = Column(Text, nullable=False)
    size = Column(BigInteger, nullable=False, default=0)
    mime_type = Column(String(255), nullable=True)

    access_type = Column(ENUM(DriveAccessType, name="driveaccesstype", create_type=True), nullable=False, server_default="public")
    allowed_role_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True, default=[])

    # Link to task attachment (for task disk virtual files)
    task_attachment_id = Column(UUID(as_uuid=True), ForeignKey("TaskAttachments.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=datetime.now())

    owner = relationship("User", foreign_keys=[owner_id])
    folder = relationship("DriveFolder", back_populates="files", foreign_keys=[folder_id])
    task_attachment = relationship("TaskAttachment", foreign_keys=[task_attachment_id])


# ─── Pydantic schemas ───

class DriveFolderPreview(PydModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    owner_id: uuid.UUID
    access_type: str
    allowed_role_ids: list[uuid.UUID] | None = None
    is_task_disk: bool = False
    created_at: datetime | None = None


class DriveFilePreview(PydModel):
    id: uuid.UUID
    folder_id: uuid.UUID | None = None
    owner_id: uuid.UUID
    name: str
    url: str
    size: int
    mime_type: str | None = None
    access_type: str
    allowed_role_ids: list[uuid.UUID] | None = None
    task_attachment_id: uuid.UUID | None = None
    created_at: datetime | None = None


class DriveListResponse(PydModel):
    folders: list[DriveFolderPreview]
    files: list[DriveFilePreview]
    current_folder: DriveFolderPreview | None = None
    breadcrumbs: list[DriveFolderPreview] = []


class TaskDiskFile(PydModel):
    id: str
    name: str
    url: str
    created_at: datetime | None = None
    board_name: str
