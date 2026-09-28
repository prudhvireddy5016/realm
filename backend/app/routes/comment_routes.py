from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ..database import query, query_returning, execute
from ..auth import get_current_user

router = APIRouter(prefix="/api/comments", tags=["comments"])


class CreateCommentRequest(BaseModel):
    content: str
    parent_comment_id: Optional[str] = None


@router.get("/post/{post_id}")
def get_comments(post_id: str):
    comments = query(
        """SELECT c.*,
                  u.username, u.display_name, u.avatar_url as author_avatar,
                  a.name as agent_name, a.role as agent_role,
                  a.avatar_url as agent_avatar, a.tone as agent_tone
           FROM comments c
           LEFT JOIN users u ON c.user_id = u.id
           LEFT JOIN agent_personas a ON c.agent_id = a.id
           WHERE c.post_id = %s
           ORDER BY c.created_at ASC""",
        (post_id,),
    )
    return comments


@router.post("/post/{post_id}", status_code=201)
def add_comment(
    post_id: str,
    req: CreateCommentRequest,
    current_user: dict = Depends(get_current_user),
):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Comment content required")

    comment = query_returning(
        """INSERT INTO comments (post_id, user_id, content, parent_comment_id, is_agent)
           VALUES (%s, %s, %s, %s, FALSE)
           RETURNING *""",
        (post_id, current_user["sub"], req.content.strip(), req.parent_comment_id),
    )

    # Update comment count
    execute(
        "UPDATE posts SET comment_count = comment_count + 1 WHERE id = %s",
        (post_id,),
    )

    # Fetch full comment with user info
    full_comment = query(
        """SELECT c.*,
                  u.username, u.display_name, u.avatar_url as author_avatar
           FROM comments c
           JOIN users u ON c.user_id = u.id
           WHERE c.id = %s""",
        (comment["id"],),
        fetch_one=True,
    )

    return full_comment
