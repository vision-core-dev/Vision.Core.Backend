from datetime import datetime, timezone

from sqlalchemy import Column, String, BigInteger, JSON, Text, Boolean, DateTime, Index

from app.Infrastructure.Database import Base


class GuildSettings(Base):
    __tablename__ = "VisionBotGuildSettings"

    guild_id = Column(BigInteger, primary_key=True)
    language = Column(String, default="uk")
    on_member_added_roles = Column(JSON, default=[])
    logs_channel_id = Column(BigInteger, nullable=True)

class Module(Base):
    __tablename__ = "VisionBotModules"

    id = Column(BigInteger, primary_key=True)
    server_id = Column(BigInteger, index=True)
    name = Column(String, nullable=False)
    code = Column(Text, nullable=False)
    meta = Column(JSON, default={})  # опис, тригери, версія, автор тощо
    status = Column(Boolean, default=True) # disabled / prepared / running / paused
    created_by = Column(BigInteger, nullable=True)  # Discord user ID
    created_at = Column(BigInteger, nullable=True)
    updated_at = Column(BigInteger, nullable=True)  # timestamp

class ModuleLog(Base):
    __tablename__ = "VisionBotModuleLogs"

    id = Column(BigInteger, primary_key=True)
    module_id = Column(BigInteger, nullable=False)
    server_id = Column(BigInteger, nullable=False)
    level = Column(String, nullable=False)  # info, warn, error, debug
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class UniversalStore(Base):
    __tablename__ = "VisionBotUniversalStore"

    id = Column(BigInteger, primary_key=True)
    server_id = Column(BigInteger, index=True)
    scope = Column(String, nullable=False)
    module_id = Column(BigInteger, nullable=True)
    name = Column(String, nullable=False)
    key = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    value_type = Column(String, nullable=False)
    value = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_universal_unique", "server_id", "scope", "module_id", "key", unique=True),
    )