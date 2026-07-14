import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.GameModel import Game
from app.Objects.GameSchemas import (
    CreateGameRequest,
    UpdateGameRequest,
    GameResponse,
    ListGamesResponse,
)
from app.Objects.GameFeedPostModel import GameFeedPost
from app.Objects.GameFeedPostSchemas import (
    CreateGameFeedPostRequest,
    UpdateGameFeedPostRequest,
    GameFeedPostResponse,
    ListGameFeedPostsResponse,
)
from app.Services.Hub.AuthService.depends import getuser, require_role
from app.Services.RoVision.content import sanitize_html

games_router = APIRouter(prefix="/Games", tags=["RoVision", "Games"])

def check_permission(user: User):
    # Content management is restricted to managers and above (order <= 3).
    require_role(user, 3)

# ---------- Admin ----------

@games_router.get("/Admin/List", response_model=ListGamesResponse)
async def admin_list(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    check_permission(user)
    stmt = select(Game).order_by(desc(Game.created_at))
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}

@games_router.get("/Admin/{game_id}", response_model=GameResponse)
async def admin_get(game_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    check_permission(user)
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@games_router.post("/Create", response_model=GameResponse)
async def create_game(
    data: CreateGameRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    check_permission(user)
    content_html = sanitize_html(data.content)
    
    new_game = Game(
        slug=data.slug,
        title=data.title,
        summary=data.summary,
        content=content_html,
        thumbnail_url=data.thumbnail_url,
        play_url=data.play_url,
        status=data.status,
        is_published=data.is_published,
        developer_slug=data.developer_slug,
    )
    
    db.add(new_game)
    try:
        await db.commit()
        await db.refresh(new_game)
        return new_game
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Slug already exists")

@games_router.patch("/{game_id}/Update", response_model=GameResponse)
async def update_game(
    game_id: uuid.UUID,
    data: UpdateGameRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    check_permission(user)
    
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
        
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "content" and v is not None:
            v = sanitize_html(v)
        setattr(game, k, v)
        
    try:
        await db.commit()
        await db.refresh(game)
        return game
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Slug already exists")

@games_router.delete("/{game_id}/Delete")
async def delete_game(
    game_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    check_permission(user)
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
        
    await db.delete(game)
    await db.commit()
    return {"status": "ok"}

# ---------- Public ----------

@games_router.get("/List", response_model=ListGamesResponse)
async def list_games(db: AsyncSession = Depends(getdb)):
    stmt = select(Game).where(Game.is_published.is_(True)).order_by(desc(Game.created_at))
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}

@games_router.get("/BySlug/{slug}", response_model=GameResponse)
async def get_game_by_slug(slug: str, db: AsyncSession = Depends(getdb)):
    result = await db.execute(select(Game).where(Game.slug == slug))
    game = result.scalar_one_or_none()

    if not game or not game.is_published:
        raise HTTPException(status_code=404, detail="Game not found")

    return game

# ---------- Feed (developer/team updates per game) ----------

@games_router.get("/{slug}/Feed", response_model=ListGameFeedPostsResponse)
async def list_game_feed(slug: str, db: AsyncSession = Depends(getdb)):
    """Public list of published feed posts for a game (by slug)."""
    game_q = await db.execute(select(Game).where(Game.slug == slug))
    game = game_q.scalar_one_or_none()
    if not game or not game.is_published:
        raise HTTPException(status_code=404, detail="Game not found")

    stmt = (
        select(GameFeedPost)
        .where(GameFeedPost.game_id == game.id)
        .where(GameFeedPost.is_published.is_(True))
        .order_by(desc(GameFeedPost.created_at))
    )
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}


@games_router.get("/{game_id}/Feed/Admin/List", response_model=ListGameFeedPostsResponse)
async def admin_list_game_feed(
    game_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    if not await db.get(Game, game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    stmt = (
        select(GameFeedPost)
        .where(GameFeedPost.game_id == game_id)
        .order_by(desc(GameFeedPost.created_at))
    )
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}


@games_router.post("/{game_id}/Feed/Create", response_model=GameFeedPostResponse)
async def create_game_feed_post(
    game_id: uuid.UUID,
    data: CreateGameFeedPostRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    if not await db.get(Game, game_id):
        raise HTTPException(status_code=404, detail="Game not found")

    post = GameFeedPost(
        game_id=game_id,
        author_id=user.id,
        developer_slug=data.developer_slug,
        title=data.title,
        content=sanitize_html(data.content),
        is_published=data.is_published,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@games_router.patch("/Feed/{post_id}/Update", response_model=GameFeedPostResponse)
async def update_game_feed_post(
    post_id: uuid.UUID,
    data: UpdateGameFeedPostRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    post = await db.get(GameFeedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Feed post not found")

    updates = data.model_dump(exclude_unset=True)
    if "content" in updates and updates["content"] is not None:
        updates["content"] = sanitize_html(updates["content"])
    for k, v in updates.items():
        setattr(post, k, v)

    await db.commit()
    await db.refresh(post)
    return post


@games_router.delete("/Feed/{post_id}/Delete")
async def delete_game_feed_post(
    post_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    post = await db.get(GameFeedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Feed post not found")
    await db.delete(post)
    await db.commit()
    return {"status": "ok"}
