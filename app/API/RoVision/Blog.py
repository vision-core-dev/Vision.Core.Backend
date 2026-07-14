import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.BlogPostModel import BlogPost
from app.Objects.BlogPostSchemas import (
    CreateBlogPostRequest,
    UpdateBlogPostRequest,
    BlogPostResponse,
    ListBlogPostsResponse,
)
from pydantic import BaseModel
import os
import openai
from app.Services.Hub.AuthService.depends import getuser, require_role
from app.Services.RoVision.content import sanitize_html, estimate_reading_time

blog_router = APIRouter(prefix="/Blog", tags=["RoVision > Blog"])


def check_permission(user: User):
    # Content management is restricted to managers and above (order <= 3).
    require_role(user, 3)


# ---------- Public ----------

@blog_router.get("/List", response_model=ListBlogPostsResponse)
async def list_posts(db: AsyncSession = Depends(getdb)):
    # Public endpoint: only published, non-embargoed posts. No draft exposure.
    stmt = (
        select(BlogPost)
        .where(BlogPost.is_published.is_(True))
        .where((BlogPost.published_at.is_(None)) | (BlogPost.published_at <= func.now()))
        .order_by(desc(BlogPost.created_at))
    )
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}


@blog_router.get("/BySlug/{slug}", response_model=BlogPostResponse)
async def get_post_by_slug(slug: str, db: AsyncSession = Depends(getdb)):
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    post = result.scalar_one_or_none()
    
    # We shouldn't need to block accessing by slug if it's not published in the future, 
    # but strictly speaking public users shouldn't see it.
    if not post or not post.is_published:
        raise HTTPException(status_code=404, detail="Post not found")
        
    import datetime
    if post.published_at and post.published_at.replace(tzinfo=datetime.timezone.utc) > datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=404, detail="Post not found")
        
    return post


# ---------- Admin ----------

class AIGenerateRequest(BaseModel):
    prompt: str
    type: str
    currentContent: str = ""

@blog_router.post("/Admin/AIGenerate")
async def ai_generate(
    data: AIGenerateRequest,
    user: User = Depends(getuser)
):
    check_permission(user)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured on server")
        
    client = openai.AsyncOpenAI(api_key=api_key)
    
    system_message = ""
    user_message = ""

    if data.type == "generate":
        system_message = "You are a professional blog writer. Generate a well-structured article in HTML format based on the user's prompt. Use appropriate heading tags (<h1>, <h2>), paragraphs (<p>), lists (<ul>, <li>), and other HTML formatting where necessary. Do NOT wrap the HTML in markdown code blocks (e.g. ```html). Output only raw HTML."
        user_message = data.prompt
    elif data.type == "adapt":
        system_message = "You are an expert editor. Adapt and improve the formatting of the provided text. Make the structure clear with headings (<h2>, <h3>), fix paragraphs, and use lists if needed. Return ONLY valid HTML. Do NOT wrap in markdown code blocks. Do not change the original meaning."
        user_message = f"Prompt/Instructions: {data.prompt}\n\nCurrent Content:\n{data.currentContent}"
    else:
        raise HTTPException(status_code=400, detail="Invalid generation type")

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
        )
        return {"content": response.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
