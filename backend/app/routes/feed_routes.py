from fastapi import APIRouter, Depends, Query

from ..database import query
from ..auth import get_optional_user

router = APIRouter(prefix="/api/feed", tags=["feed"])


@router.get("/")
def get_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_optional_user),
):
    offset = (page - 1) * limit
    user_id = current_user["sub"] if current_user else None

    posts = query(
        """SELECT p.*,
                  u.username, u.display_name, u.avatar_url as author_avatar,
                  COALESCE(
                    (SELECT json_agg(
                      json_build_object(
                        'id', c.id,
                        'content', c.content,
                        'is_agent', c.is_agent,
                        'created_at', c.created_at,
                        'username', cu.username,
                        'display_name', cu.display_name,
                        'author_avatar', cu.avatar_url,
                        'agent_name', ca.name,
                        'agent_role', ca.role,
                        'agent_avatar', ca.avatar_url,
                        'agent_tone', ca.tone
                      ) ORDER BY c.created_at ASC
                    )
                    FROM comments c
                    LEFT JOIN users cu ON c.user_id = cu.id
                    LEFT JOIN agent_personas ca ON c.agent_id = ca.id
                    WHERE c.post_id = p.id)
                  , '[]'::json) as comments,
                  CASE WHEN %s::uuid IS NOT NULL THEN
                    EXISTS(SELECT 1 FROM likes l WHERE l.post_id = p.id AND l.user_id = %s)
                  ELSE FALSE END as liked_by_me
           FROM posts p
           JOIN users u ON p.user_id = u.id
           ORDER BY p.created_at DESC
           LIMIT %s OFFSET %s""",
        (user_id, user_id, limit, offset),
    )

    # Get total count
    count_result = query("SELECT COUNT(*) as total FROM posts", fetch_one=True)
    total = count_result["total"] if count_result else 0

    return {
        "posts": posts,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": max(1, -(-total // limit)),  # ceiling division
        },
    }
