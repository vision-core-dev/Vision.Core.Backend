from fastapi import APIRouter
from pydantic import BaseModel

from app.Objects.BadgeModel import UserBadgeBase
from app.Objects.UserModel import UserBase

my_profile_router = APIRouter()

class MyProfileResponse(BaseModel):
    user: UserBase
    badges: list[UserBadgeBase]
    cases: list[str]


@my_profile_router.get("/MyProfile")
async def get_my_profile():
