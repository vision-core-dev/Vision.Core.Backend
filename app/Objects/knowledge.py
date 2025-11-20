import enum

from sqlalchemy import ForeignKey, func, Column, UUID, String, DateTime, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship
from app.Infrastructure.Database import Base

class KnowledgeAccessLevel(enum.Enum):
    READ = "read"
    WRITE = "write"

class KnowledgeAccess(Base):
    __tablename__ = "KnowledgeAccess"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    role_id = Column(UUID(as_uuid=True), ForeignKey("UserRoles.id"), nullable=False, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("KnowledgeFolders.id"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("KnowledgeDocuments.id"), nullable=True)

    # 👇 "read" – може читати, "write" – створювати нові версії
    access_level = Column(ENUM(KnowledgeAccessLevel), nullable=False, default="read")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    folder = relationship("KnowledgeFolder")
    document = relationship("KnowledgeDocument")

class KnowledgeFolder(Base):
    __tablename__ = "KnowledgeFolders"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(200), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("KnowledgeFolders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subfolders = relationship(
        "KnowledgeFolder",
        backref="parent",
        remote_side=[id],
        lazy="selectin",
        cascade="all, delete"
    )
    documents = relationship("KnowledgeDocument", back_populates="folder", lazy="selectin")


class KnowledgeVersion(Base):
    __tablename__ = "KnowledgeVersions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id = Column(UUID(as_uuid=True), ForeignKey("KnowledgeDocuments.id"))
    content = Column(Text, nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("KnowledgeDocument", back_populates="versions")


class KnowledgeDocument(Base):
    __tablename__ = "KnowledgeDocuments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title = Column(String(200), nullable=False, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("KnowledgeFolders.id"), nullable=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"), nullable=False, index=True)

    # raw UUID for current version
    current_version_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ---------- RELATIONSHIPS ----------

    folder = relationship(
        "KnowledgeFolder",
        back_populates="documents",
        lazy="selectin"
    )

    # 🧑‍💻 Автор документа
    author = relationship(
        "User",
        lazy="joined"
    )

    # 📝 Поточна версія документа
    current_version = relationship(
        "KnowledgeVersion",
        primaryjoin="foreign(KnowledgeDocument.current_version_id)==KnowledgeVersion.id",
        lazy="joined",
        viewonly=True
    )

    # 📚 Всі версії документа
    versions = relationship(
        "KnowledgeVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
