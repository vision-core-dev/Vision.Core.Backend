import uuid

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User



async def get_token(
    authorization: str | None = Header(None)
) -> uuid.UUID:

    raw_token = None

    if authorization:
        if authorization.lower().startswith("bearer "):
            raw_token = authorization.split(" ", 1)[1].strip()
        else:
            raw_token = authorization.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_authentication_token"
        )

    try:
        token_uuid = uuid.UUID(str(raw_token))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_token_format"
        )

    return token_uuid

async def getuser(
    db: AsyncSession = Depends(getdb),
    token: uuid.UUID = Depends(get_token),
    is_accepting_terms: bool = False,
    is_check_me: bool = False,
):
    return await _get_user_by_token(db, token, is_accepting_terms, is_check_me)


# Дозволяє перевірку користувача (CheckMe)
async def getuser_check_me(
    db: AsyncSession = Depends(getdb),
    token: uuid.UUID = Depends(get_token),
):
    return await _get_user_by_token(db, token, is_check_me=True)

# Дозволяє AcceptOffer навіть без terms
async def getuser_accepting_terms(
    db: AsyncSession = Depends(getdb),
    token: uuid.UUID = Depends(get_token),
):
    return await _get_user_by_token(db, token, is_accepting_terms=True)


async def _get_user_by_token(
    db: AsyncSession,
    token: uuid.UUID,
    is_accepting_terms: bool = False,
    is_check_me: bool = False,
):
    q = (
        select(User)
        .options(selectinload(User.role))
        .filter(User.temp_token == token)
    )

    result = await db.execute(q)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="user_is_deactivated")

    # 🧠 Якщо не акцепт і не CheckMe — блокуємо
    if not (is_accepting_terms or is_check_me):
        if user.is_need_accept_terms and not user.is_terms_accepted:
            raise HTTPException(status_code=403, detail="terms_not_accepted")

    _ = user.role.order
    return user
