import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.BlogPostModel import BlogPost
from app.Objects.BlogPostSchemas import (
    CreateBlogPostRequest,
    UpdateBlogPostRequest,
    BlogPostResponse,
    ListBlogPostsResponse,
)
from app.Services.Hub.AuthService.depends import getuser
from app.Services.RoVision.content import sanitize_html, estimate_reading_time

blog_router = APIRouter(prefix="/Blog", tags=["RoVision > Blog"])


def check_permission(user: User):
    if not user.role or user.role.order not in [0, 1]:
        raise HTTPException(status_code=403, detail="Тільки CEO/COO можуть керувати блогом")


# ---------- Public ----------

@blog_router.get("/List", response_model=ListBlogPostsResponse)
async def list_posts(db: AsyncSession = Depends(getdb), include_unpublished: bool = False):
    stmt = select(BlogPost).order_by(desc(BlogPost.created_at))
    if not include_unpublished:
        stmt = stmt.where(BlogPost.is_published.is_(True))
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}


@blog_router.get("/BySlug/{slug}", response_model=BlogPostResponse)
async def get_post_by_slug(slug: str, db: AsyncSession = Depends(getdb)):
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    post = result.scalar_one_or_none()
    if not post or not post.is_published:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# ---------- Admin ----------

@blog_router.get("/Admin/List", response_model=ListBlogPostsResponse)
async def admin_list(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    check_permission(user)
    result = await db.execute(select(BlogPost).order_by(desc(BlogPost.created_at)))
    return {"items": result.scalars().all()}


@blog_router.get("/Admin/{post_id}", response_model=BlogPostResponse)
async def admin_get(post_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    check_permission(user)
    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@blog_router.post("/Create", response_model=BlogPostResponse)
async def create_post(
    data: CreateBlogPostRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)

    existing = await db.execute(select(BlogPost).where(BlogPost.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug вже існує")

    payload = data.model_dump()
    payload["content"] = sanitize_html(payload.get("content"))
    if not payload.get("reading_time"):
        payload["reading_time"] = estimate_reading_time(payload["content"])

    post = BlogPost(author_id=user.id, **payload)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@blog_router.patch("/{post_id}/Update", response_model=BlogPostResponse)
async def update_post(
    post_id: uuid.UUID,
    data: UpdateBlogPostRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)

    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    updates = data.model_dump(exclude_unset=True)
    if "content" in updates:
        updates["content"] = sanitize_html(updates["content"])
        if not updates.get("reading_time"):
            updates["reading_time"] = estimate_reading_time(updates["content"])
    for key, value in updates.items():
        setattr(post, key, value)

    await db.commit()
    await db.refresh(post)
    return post


@blog_router.delete("/{post_id}/Delete")
async def delete_post(
    post_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)

    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.delete(post)
    await db.commit()
    return {"status": "success"}
