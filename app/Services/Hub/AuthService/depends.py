import uuid

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
):
    return await _get_user_by_token(db, token)

async def _get_user_by_token(
    db: AsyncSession,
    token: uuid.UUID,
    raise_on_none: bool = True
):
    q = select(User).filter(User.temp_token == token)

    result = await db.execute(q)
    user = result.scalar_one_or_none()

    if not user:
        if raise_on_none:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_or_expired_token",
            )
        else:
            return None

    return user