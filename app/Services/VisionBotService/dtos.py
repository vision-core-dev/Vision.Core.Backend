from pydantic import BaseModel
from typing import Optional, Any, List


# ───────────────────────────────────────────────
# Guild Settings
# ───────────────────────────────────────────────

class GuildSettingsDTO(BaseModel):
    guild_id: str
    language: str
    logs_channel_id: Optional[int]
    on_member_added_roles: list[int]


class UpdateGuildSettingsDTO(BaseModel):
    language: Optional[str] = None
    logs_channel_id: Optional[int] = None
    on_member_added_roles: Optional[List[int]] = None


# ───────────────────────────────────────────────
# Modules
# ───────────────────────────────────────────────

class ModuleDTO(BaseModel):
    id: str
    server_id: str
    name: str
    code: str
    meta: dict | None
    status: bool
    created_by: int | None
    created_at: int | None
    updated_at: int | None


class UpdateModuleDTO(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    meta: Optional[dict] = None
    status: Optional[bool] = None


# ───────────────────────────────────────────────
# Logs
# ───────────────────────────────────────────────

class ModuleLogDTO(BaseModel):
    id: str
    module_id: str
    server_id: str
    level: str
    message: str
    timestamp: str


# ───────────────────────────────────────────────
# Universal Store
# ───────────────────────────────────────────────

class UniversalStoreItemDTO(BaseModel):
    id: str
    server_id: str
    scope: str
    module_id: Optional[int]
    name: str
    key: str
    data_type: str
    value_type: str
    value: Any


class SetUniversalStoreItemDTO(BaseModel):
    server_id: str
    scope: str
    module_id: Optional[int]
    name: str
    key: str
    data_type: str
    value_type: str
    value: Any
