from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser, require_role
from app.Services.VisionBotService import VisionBotService

from app.Services.VisionBotService.dtos import (
    GuildSettingsDTO,
    UpdateGuildSettingsDTO,
    ModuleDTO,
    UpdateModuleDTO,
    ModuleLogDTO,
    UniversalStoreItemDTO,
    SetUniversalStoreItemDTO
)

vision_bot_router = APIRouter(prefix="/VisionBot", tags=["VisionBot"])


# ----------------------------------------------------------
# DICT SERIALIZER
# ----------------------------------------------------------

def to_dict(model, string_ids: list[str] = None):
    data = {}

    for k, v in model.__dict__.items():
        if k.startswith("_"):
            continue

        if string_ids and k in string_ids and v is not None:
            data[k] = str(v)
        else:
            data[k] = v

    return data


# ----------------------------------------------------------
# SERVERS
# ----------------------------------------------------------

@vision_bot_router.get("/Servers/GetAll")
async def get_all_servers(
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    servers = await VisionBotService(db).get_all_servers()

    return [
        GuildSettingsDTO.model_validate(
            to_dict(s, string_ids=["guild_id", "logs_channel_id"])
        )
        for s in servers
    ]


@vision_bot_router.get("/Servers/{guild_id}/Get")
async def get_guild(
    guild_id: int,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    guild = await VisionBotService(db).get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="guild_not_found")

    return GuildSettingsDTO.model_validate(
        to_dict(guild, string_ids=["guild_id", "logs_channel_id"])
    )


@vision_bot_router.post("/Servers/{guild_id}/Update")
async def update_guild_settings(
    guild_id: int,
    payload: UpdateGuildSettingsDTO,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    require_role(user, 2)
    updated = await VisionBotService(db).update_guild_settings(
        guild_id,
        **{k: v for k, v in payload.dict().items() if v is not None}
    )

    return GuildSettingsDTO.model_validate(
        to_dict(updated, string_ids=["guild_id", "logs_channel_id"])
    )


# ----------------------------------------------------------
# MODULES
# ----------------------------------------------------------

@vision_bot_router.get("/Modules/Get")
async def get_modules(
    guild_id: int,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    modules = await VisionBotService(db).get_modules(guild_id)

    return [
        ModuleDTO.model_validate(
            to_dict(m, string_ids=["id", "server_id", "created_by"])
        )
        for m in modules
    ]


@vision_bot_router.get("/Modules/{module_id}/Get")
async def get_module(
    module_id: int,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    module = await VisionBotService(db).get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="module_not_found")

    return ModuleDTO.model_validate(
        to_dict(module, string_ids=["id", "server_id", "created_by"])
    )


@vision_bot_router.post("/Modules/{module_id}/Update")
async def update_module(
    module_id: int,
    payload: UpdateModuleDTO,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    require_role(user, 2)
    updated = await VisionBotService(db).update_module(
        module_id,
        **{k: v for k, v in payload.dict().items() if v is not None}
    )

    return ModuleDTO.model_validate(
        to_dict(updated, string_ids=["id", "server_id", "created_by"])
    )


@vision_bot_router.post("/Modules/{module_id}/Delete")
async def delete_module(
    module_id: int,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    require_role(user, 2)
    await VisionBotService(db).delete_module(module_id)
    return {"status": "ok"}


# ----------------------------------------------------------
# LOGS
# ----------------------------------------------------------

@vision_bot_router.get("/Logs/Get")
async def get_logs(
    guild_id: int,
    module_id: int | None = None,
    level: str | None = None,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    logs = await VisionBotService(db).get_logs(guild_id, module_id, level)

    return [
        ModuleLogDTO.model_validate({
            **to_dict(l, string_ids=["id", "module_id", "server_id"]),
            "timestamp": l.timestamp.isoformat() if l.timestamp else None
        })
        for l in logs
    ]


# ----------------------------------------------------------
# UNIVERSAL STORE
# ----------------------------------------------------------

@vision_bot_router.get("/Store/Get")
async def get_store_items(
    guild_id: int,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    items = await VisionBotService(db).get_store_items(guild_id)

    return [
        UniversalStoreItemDTO.model_validate(
            to_dict(i, string_ids=["id", "server_id"])
        )
        for i in items
    ]


@vision_bot_router.get("/Store/{item_id}/Get")
async def get_store_item(
    item_id: int,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    item = await VisionBotService(db).get_store_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="store_item_not_found")

    return UniversalStoreItemDTO.model_validate(
        to_dict(item, string_ids=["id", "server_id"])
    )


@vision_bot_router.post("/Store/Set")
async def set_store_item(
    payload: SetUniversalStoreItemDTO,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    require_role(user, 2)
    item = await VisionBotService(db).set_store_item(**payload.dict())

    return UniversalStoreItemDTO.model_validate(
        to_dict(item, string_ids=["id", "server_id"])
    )


@vision_bot_router.post("/Store/{item_id}/Delete")
async def delete_store_item(
    item_id: int,
    user=Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    require_role(user, 2)
    await VisionBotService(db).delete_store_item(item_id)
    return {"status": "ok"}
