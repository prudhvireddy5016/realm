from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from ..database import query, query_returning, execute
from ..auth import get_current_user
from ..agents import agent_engine

router = APIRouter(prefix="/api/posts", tags=["posts"])


class CreatePostRequest(BaseModel):
    content: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    tags: list[str] = []


@router.post("/", status_code=201)
def create_post(
    req: CreatePostRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Post content is required")

    post = query_returning(
        """INSERT INTO posts (user_id, content, media_url, media_type, tags)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING *""",
        (
            current_user["sub"],
            req.content.strip(),
            req.media_url,
            req.media_type,
            req.tags,
        ),
    )

    # Trigger agent engagement in background
    background_tasks.add_task(
        agent_engine.engage,
        str(post["id"]),
        post["content"],
        post["tags"] or [],
    )

    return post


@router.get("/{post_id}")
def get_post(post_id: str):
    post = query(
        """SELECT p.*,
                  u.username, u.display_name, u.avatar_url as author_avatar
           FROM posts p
           JOIN users u ON p.user_id = u.id
           WHERE p.id = %s""",
        (post_id,),
        fetch_one=True,
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.delete("/{post_id}")
def delete_post(post_id: str, current_user: dict = Depends(get_current_user)):
    result = query_returning(
        "DELETE FROM posts WHERE id = %s AND user_id = %s RETURNING id",
        (post_id, current_user["sub"]),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Post not found or unauthorized")
    return {"message": "Post deleted"}


@router.post("/{post_id}/like")
def toggle_like(post_id: str, current_user: dict = Depends(get_current_user)):
    # Check if already liked
    existing = query(
        "SELECT id FROM likes WHERE post_id = %s AND user_id = %s",
        (post_id, current_user["sub"]),
    )

    if existing:
        execute(
            "DELETE FROM likes WHERE post_id = %s AND user_id = %s",
            (post_id, current_user["sub"]),
        )
        execute("UPDATE posts SET like_count = like_count - 1 WHERE id = %s", (post_id,))
        return {"liked": False}

    execute(
        "INSERT INTO likes (post_id, user_id) VALUES (%s, %s)",
        (post_id, current_user["sub"]),
    )
    execute("UPDATE posts SET like_count = like_count + 1 WHERE id = %s", (post_id,))
    return {"liked": True}
