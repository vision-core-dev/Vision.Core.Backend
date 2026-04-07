import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Body

from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser

kolektoral_router = APIRouter(prefix="/Kolektoral", tags=["Hub > Kolektoral"])

KOLEKTORAL_URL = os.getenv("KOLEKTORAL_URL", "http://localhost:3000")
KOLEKTORAL_TOKEN = os.getenv("KOLEKTORAL_TOKEN", "")


def _headers():
    return {"Authorization": f"Bearer {KOLEKTORAL_TOKEN}"}


def _check_access(user: User):
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")


async def _proxy_get(path: str):
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(f"{KOLEKTORAL_URL}{path}", headers=_headers())
        return res.json()


async def _proxy_post(path: str, json: dict):
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(f"{KOLEKTORAL_URL}{path}", json=json, headers=_headers())
        return res.json()


async def _proxy_delete(path: str, json: dict):
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.request("DELETE", f"{KOLEKTORAL_URL}{path}", json=json, headers=_headers())
        return res.json()


@kolektoral_router.get("/Players")
async def list_players(user: User = Depends(getuser)):
    _check_access(user)
    return await _proxy_get("/players/list")


@kolektoral_router.get("/Players/{roblox_id}")
async def get_player(roblox_id: int, user: User = Depends(getuser)):
    _check_access(user)
    return await _proxy_get(f"/certificates/players/{roblox_id}")


@kolektoral_router.get("/Players/{roblox_id}/Join")
async def player_join(roblox_id: int, user: User = Depends(getuser)):
    _check_access(user)
    data = await _proxy_get(f"/player-join/{roblox_id}")
    return {"player": data.get("result")}


@kolektoral_router.get("/Certificates")
async def list_certificate_types(user: User = Depends(getuser)):
    _check_access(user)
    return await _proxy_get("/certificates/players/types")


@kolektoral_router.post("/Players/{roblox_id}/Certificates/Issue")
async def issue_certificate(roblox_id: int, data: dict = Body(...), user: User = Depends(getuser)):
    _check_access(user)
    return await _proxy_post(
        f"/certificates/players/{roblox_id}",
        {"shortCode": data["short_code"], "invoker": int(user.roblox_id or 0)},
    )


@kolektoral_router.post("/Players/{roblox_id}/Certificates/Revoke")
async def revoke_certificate(roblox_id: int, data: dict = Body(...), user: User = Depends(getuser)):
    _check_access(user)
    return await _proxy_delete(
        f"/certificates/players/{roblox_id}",
        {"shortCode": data["short_code"]},
    )
