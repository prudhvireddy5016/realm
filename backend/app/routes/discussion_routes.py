import uuid as uuid_lib
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from ..database import query, query_returning, execute
from ..auth import get_current_user, get_optional_user
from ..agents import agent_engine
from ..orgs import get_org_or_404, require_read_access, require_member, require_role

router = APIRouter(prefix="/api", tags=["discussions"])


class CreateDiscussionRequest(BaseModel):
    title: str
    body: Optional[str] = None
    tags: list[str] = []


class UpdateDiscussionRequest(BaseModel):
    is_pinned: Optional[bool] = None
    is_locked: Optional[bool] = None


class CreateReplyRequest(BaseModel):
    content: str
    parent_reply_id: Optional[str] = None


def _uuid_or_404(value: str, label: str = "Discussion") -> str:
    """Reject malformed UUIDs with a 404 instead of letting psycopg2 500."""
    try:
        return str(uuid_lib.UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail=f"{label} not found")


def _load_discussion(discussion_id: str) -> tuple[dict, dict]:
    """Fetch a discussion together with its org, or 404."""
    discussion_id = _uuid_or_404(discussion_id)
    discussion = query(
        """SELECT d.*, u.username, u.display_name, u.avatar_url as author_avatar,
                  o.slug as org_slug, o.name as org_name
           FROM discussions d
           JOIN users u ON u.id = d.user_id
           JOIN organizations o ON o.id = d.org_id
           WHERE d.id = %s""",
        (discussion_id,),
        fetch_one=True,
    )
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    org = get_org_or_404(discussion["org_slug"])
    return discussion, org


def _sync_reply_count(discussion_id: str):
    """Recompute reply_count from source — cascading deletes make deltas drift."""
    execute(
        """UPDATE discussions
           SET reply_count = (SELECT COUNT(*) FROM discussion_replies
                               WHERE discussion_id = %s)
           WHERE id = %s""",
        (discussion_id, discussion_id),
    )


# ---------------------------------------------------------------------------
# Discussions within an org
# ---------------------------------------------------------------------------


@router.get("/orgs/{slug}/discussions")
def list_discussions(slug: str, current_user: dict = Depends(get_optional_user)):
    org = get_org_or_404(slug)
    require_read_access(org, current_user["sub"] if current_user else None)

    return query(
        """SELECT d.id, d.title, d.body, d.tags, d.is_pinned, d.is_locked,
                  d.reply_count, d.last_activity_at, d.created_at,
                  u.username, u.display_name, u.avatar_url as author_avatar
           FROM discussions d
           JOIN users u ON u.id = d.user_id
           WHERE d.org_id = %s
           ORDER BY d.is_pinned DESC, d.last_activity_at DESC""",
        (str(org["id"]),),
    )


@router.post("/orgs/{slug}/discussions", status_code=201)
def create_discussion(
    slug: str,
    req: CreateDiscussionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    org = get_org_or_404(slug)
    require_member(org, current_user["sub"])

    title = req.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Discussion title is required")

    discussion = query_returning(
        """INSERT INTO discussions (org_id, user_id, title, body, tags)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING *""",
        (str(org["id"]), current_user["sub"], title, (req.body or "").strip(), req.tags),
    )

    # Agents join the thread in the background, same as they do on posts.
    background_tasks.add_task(
        agent_engine.engage_discussion,
        str(discussion["id"]),
        title,
        discussion["body"] or "",
        discussion["tags"] or [],
    )

    return discussion


@router.get("/discussions/{discussion_id}")
def get_discussion(discussion_id: str, current_user: dict = Depends(get_optional_user)):
    discussion, org = _load_discussion(discussion_id)
    role = require_read_access(org, current_user["sub"] if current_user else None)

    replies = query(
        """SELECT r.id, r.parent_reply_id, r.content, r.is_agent, r.created_at,
                  u.username, u.display_name, u.avatar_url as author_avatar,
                  a.name as agent_name, a.role as agent_role,
                  a.avatar_url as agent_avatar, a.tone as agent_tone
           FROM discussion_replies r
           LEFT JOIN users u ON u.id = r.user_id
           LEFT JOIN agent_personas a ON a.id = r.agent_id
           WHERE r.discussion_id = %s
           ORDER BY r.created_at ASC""",
        (str(discussion["id"]),),
    )

    discussion = dict(discussion)
    discussion["replies"] = replies
    discussion["my_role"] = role
    return discussion


@router.patch("/discussions/{discussion_id}")
def update_discussion(
    discussion_id: str,
    req: UpdateDiscussionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Pin or lock a thread. Org admins and owners only."""
    discussion, org = _load_discussion(discussion_id)
    require_role(org, current_user["sub"], "admin")

    updates = {
        k: v
        for k, v in (("is_pinned", req.is_pinned), ("is_locked", req.is_locked))
        if v is not None
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    return query_returning(
        f"UPDATE discussions SET {set_clause} WHERE id = %s RETURNING *",
        tuple(updates.values()) + (str(discussion["id"]),),
    )


@router.delete("/discussions/{discussion_id}")
def delete_discussion(discussion_id: str, current_user: dict = Depends(get_current_user)):
    discussion, org = _load_discussion(discussion_id)

    is_author = str(discussion["user_id"]) == current_user["sub"]
    if not is_author:
        require_role(org, current_user["sub"], "admin")

    execute("DELETE FROM discussions WHERE id = %s", (str(discussion["id"]),))
    return {"message": "Discussion deleted"}


# ---------------------------------------------------------------------------
# Replies (nested)
# ---------------------------------------------------------------------------


@router.post("/discussions/{discussion_id}/replies", status_code=201)
def add_reply(
    discussion_id: str,
    req: CreateReplyRequest,
    current_user: dict = Depends(get_current_user),
):
    discussion, org = _load_discussion(discussion_id)
    require_member(org, current_user["sub"])

    if discussion["is_locked"]:
        raise HTTPException(status_code=403, detail="This discussion is locked")

    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Reply content is required")

    parent_id = None
    if req.parent_reply_id:
        parent_id = _uuid_or_404(req.parent_reply_id, "Parent reply")
        parent = query(
            "SELECT id FROM discussion_replies WHERE id = %s AND discussion_id = %s",
            (parent_id, str(discussion["id"])),
            fetch_one=True,
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent reply not found")

    reply = query_returning(
        """INSERT INTO discussion_replies
           (discussion_id, parent_reply_id, user_id, content, is_agent)
           VALUES (%s, %s, %s, %s, FALSE)
           RETURNING id""",
        (str(discussion["id"]), parent_id, current_user["sub"], content),
    )

    execute(
        """UPDATE discussions
           SET reply_count = reply_count + 1, last_activity_at = NOW()
           WHERE id = %s""",
        (str(discussion["id"]),),
    )

    return query(
        """SELECT r.id, r.parent_reply_id, r.content, r.is_agent, r.created_at,
                  u.username, u.display_name, u.avatar_url as author_avatar
           FROM discussion_replies r
           JOIN users u ON u.id = r.user_id
           WHERE r.id = %s""",
        (str(reply["id"]),),
        fetch_one=True,
    )


@router.delete("/discussions/{discussion_id}/replies/{reply_id}")
def delete_reply(
    discussion_id: str,
    reply_id: str,
    current_user: dict = Depends(get_current_user),
):
    discussion, org = _load_discussion(discussion_id)
    reply_id = _uuid_or_404(reply_id, "Reply")

    reply = query(
        "SELECT id, user_id FROM discussion_replies WHERE id = %s AND discussion_id = %s",
        (reply_id, str(discussion["id"])),
        fetch_one=True,
    )
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    is_author = reply["user_id"] and str(reply["user_id"]) == current_user["sub"]
    if not is_author:
        require_role(org, current_user["sub"], "admin")

    execute("DELETE FROM discussion_replies WHERE id = %s", (reply_id,))
    _sync_reply_count(str(discussion["id"]))
    return {"message": "Reply deleted"}
