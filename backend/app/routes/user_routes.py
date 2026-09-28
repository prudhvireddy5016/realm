from fastapi import APIRouter, HTTPException, Depends

from ..database import query, execute
from ..auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{username}")
def get_user_profile(username: str, current_user: dict = Depends(get_optional_user)):
    user_id = current_user["sub"] if current_user else None

    profile = query(
        """SELECT u.id, u.username, u.display_name, u.avatar_url, u.bio, u.created_at,
                  (SELECT COUNT(*) FROM posts WHERE user_id = u.id) as post_count,
                  (SELECT COUNT(*) FROM follows WHERE following_id = u.id) as follower_count,
                  (SELECT COUNT(*) FROM follows WHERE follower_id = u.id) as following_count,
                  CASE WHEN %s::uuid IS NOT NULL THEN
                    EXISTS(SELECT 1 FROM follows WHERE follower_id = %s AND following_id = u.id)
                  ELSE FALSE END as is_following
           FROM users u
           WHERE u.username = %s""",
        (user_id, user_id, username),
        fetch_one=True,
    )

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@router.get("/{username}/posts")
def get_user_posts(username: str):
    posts = query(
        """SELECT p.*, u.username, u.display_name, u.avatar_url as author_avatar
           FROM posts p
           JOIN users u ON p.user_id = u.id
           WHERE u.username = %s
           ORDER BY p.created_at DESC
           LIMIT 50""",
        (username,),
    )
    return posts


@router.post("/{username}/follow")
def toggle_follow(username: str, current_user: dict = Depends(get_current_user)):
    target = query(
        "SELECT id FROM users WHERE username = %s",
        (username,),
        fetch_one=True,
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target_id = str(target["id"])
    if target_id == current_user["sub"]:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    existing = query(
        "SELECT id FROM follows WHERE follower_id = %s AND following_id = %s",
        (current_user["sub"], target_id),
    )

    if existing:
        execute(
            "DELETE FROM follows WHERE follower_id = %s AND following_id = %s",
            (current_user["sub"], target_id),
        )
        return {"following": False}

    execute(
        "INSERT INTO follows (follower_id, following_id) VALUES (%s, %s)",
        (current_user["sub"], target_id),
    )
    return {"following": True}
