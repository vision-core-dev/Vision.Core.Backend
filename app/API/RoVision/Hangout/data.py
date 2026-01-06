from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from starlette import status

from app.API.RoVision.Hangout.game_data import HangoutUserData
from app.Infrastructure.Mongo import getrvhmongo

hangout_data_router = APIRouter()
hangout_token = "HEyd6U7!5T3$7nTbyq$wWVfvAbjAV*h#mqaZ3TdfV6HUVe6FgbPpGfCAYAz7yyAP"

class GetUserDataRequest(BaseModel):
    rbx_user_id: Optional[int] = None
    create_if_not_exists: Optional[bool] = False

class UserDataResponse(BaseModel):
    user_data: Optional[HangoutUserData]

def normalize_user(doc: dict) -> HangoutUserData:
    doc["_id"] = str(doc["_id"])
    return HangoutUserData(**doc)

async def _token(
    authorization: str | None = Header(None)
) -> bool:

    raw_token = None

    if authorization:
        if authorization.lower().startswith("bearer "):
            raw_token = authorization.split(" ", 1)[1].strip()
        else:
            raw_token = authorization.strip()

    if raw_token == hangout_token:
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing_authentication_token"
    )

@hangout_data_router.post("/Users/GetUserData", response_model=UserDataResponse)
async def get_user_data(
    data: GetUserDataRequest,
    token: bool = Depends(_token),
    mongo: AsyncIOMotorDatabase = Depends(getrvhmongo)
):
    collection = mongo["users"]

    user = await collection.find_one(
        {"rbx_user_id": data.rbx_user_id}
    )

    if user:
        normalized = normalize_user(user)

        await collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": normalized.dict(
                    by_alias=True,
                    exclude={"_id", "id"}
                )
            }
        )

        return {"user_data": normalized}

    if not data.create_if_not_exists:
        return {"user_data": None}

    new_user = HangoutUserData(
        rbx_user_id=data.rbx_user_id,
    )

    result = await collection.insert_one(
        new_user.dict(
            by_alias=True,
            exclude={"_id", "id"}
        )
    )

    new_user.id = str(result.inserted_id)

    return {"user_data": new_user}

class SaveUserDataRequest(BaseModel):
    user_data: HangoutUserData

class SaveUserDataResponse(BaseModel):
    success: bool

@hangout_data_router.post("/Users/SaveUserData", response_model=SaveUserDataResponse)
async def save_user_data(
    data: SaveUserDataRequest,
    token: bool = Depends(_token),
    mongo: AsyncIOMotorDatabase = Depends(getrvhmongo)
):
    collection = mongo["users"]

    if not data.user_data.id:
        return {"success": False}

    await collection.update_one(
        {"_id": ObjectId(data.user_data.id)},
        {
            "$set": data.user_data.dict(
                by_alias=True,
                exclude={"_id", "id"}
            )
        }
    )

    return {"success": True}