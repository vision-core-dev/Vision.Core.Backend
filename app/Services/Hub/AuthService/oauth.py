import hashlib
import hmac
import os
import time
from typing import Optional

import httpx
from pydantic import BaseModel


class OAuthUserInfo(BaseModel):
    provider: str
    provider_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

ROBLOX_CLIENT_ID = os.getenv("ROBLOX_CLIENT_ID", "")
ROBLOX_CLIENT_SECRET = os.getenv("ROBLOX_CLIENT_SECRET", "")


async def get_google_user(code: str, redirect_uri: str) -> OAuthUserInfo:
    async with httpx.AsyncClient() as client:
        token_res = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        token_res.raise_for_status()
        access_token = token_res.json()["access_token"]

        user_res = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={
            "Authorization": f"Bearer {access_token}",
        })
        user_res.raise_for_status()
        data = user_res.json()

    return OAuthUserInfo(
        provider="google",
        provider_id=str(data["id"]),
        email=data.get("email"),
        username=data.get("email"),
    )


async def get_discord_user(code: str, redirect_uri: str) -> OAuthUserInfo:
    async with httpx.AsyncClient() as client:
        token_res = await client.post("https://discord.com/api/v10/oauth2/token", data={
            "code": code,
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        token_res.raise_for_status()
        access_token = token_res.json()["access_token"]

        user_res = await client.get("https://discord.com/api/v10/users/@me", headers={
            "Authorization": f"Bearer {access_token}",
        })
        user_res.raise_for_status()
        data = user_res.json()

    avatar_url = None
    if data.get("avatar"):
        avatar_url = f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png?size=512"

    return OAuthUserInfo(
        provider="discord",
        provider_id=str(data["id"]),
        username=data.get("username"),
        email=data.get("email"),
        avatar_url=avatar_url,
    )


def verify_telegram_auth(auth_data: dict) -> OAuthUserInfo:
    # Filter out None values — Telegram only includes present fields in hash
    auth_data = {k: v for k, v in auth_data.items() if v is not None}

    check_hash = auth_data.pop("hash", None)
    if not check_hash:
        raise ValueError("missing_hash")

    auth_date = auth_data.get("auth_date")
    if auth_date and (time.time() - int(auth_date)) > 86400:
        raise ValueError("auth_data_expired")

    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    sorted_data = "\n".join(f"{k}={v}" for k, v in sorted(auth_data.items()))
    computed_hash = hmac.new(secret_key, sorted_data.encode(), hashlib.sha256).hexdigest()

    if computed_hash != check_hash:
        raise ValueError("invalid_telegram_hash")

    return OAuthUserInfo(
        provider="telegram",
        provider_id=str(auth_data["id"]),
        username=auth_data.get("username"),
    )


async def get_roblox_user(code: str, redirect_uri: str) -> OAuthUserInfo:
    async with httpx.AsyncClient() as client:
        token_res = await client.post("https://apis.roblox.com/oauth/v1/token", data={
            "code": code,
            "client_id": ROBLOX_CLIENT_ID,
            "client_secret": ROBLOX_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        token_res.raise_for_status()
        access_token = token_res.json()["access_token"]

        user_res = await client.get("https://apis.roblox.com/oauth/v1/userinfo", headers={
            "Authorization": f"Bearer {access_token}",
        })
        user_res.raise_for_status()
        data = user_res.json()

    return OAuthUserInfo(
        provider="roblox",
        provider_id=str(data["sub"]),
        username=data.get("preferred_username") or data.get("name"),
    )
