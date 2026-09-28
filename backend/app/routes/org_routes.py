import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional

from ..database import query, query_returning, execute, get_db
from ..auth import get_current_user, get_optional_user
from ..orgs import (
    slugify,
    get_org_or_404,
    get_member_role,
    require_read_access,
    require_member,
    require_role,
)

router = APIRouter(prefix="/api/orgs", tags=["organizations"])


class CreateOrgRequest(BaseModel):
    name: str
    description: Optional[str] = None
    slug: Optional[str] = None
    visibility: str = "public"
    tags: list[str] = []


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    visibility: Optional[str] = None
    tags: Optional[list[str]] = None


class AddMemberRequest(BaseModel):
    username: str
    role: str = "member"


class UpdateMemberRequest(BaseModel):
    role: str


def _unique_slug(desired: str) -> str:
    """Find a free slug, appending -2, -3, ... on collision."""
    base = slugify(desired)
    slug = base
    n = 2
    while query("SELECT 1 FROM organizations WHERE slug = %s", (slug,), fetch_one=True):
        slug = f"{base[:46]}-{n}"
        n += 1
    return slug


@router.get("")
def list_orgs(
    mine: bool = Query(False, description="Only orgs the current user belongs to"),
    current_user: dict = Depends(get_optional_user),
):
    """
    List organizations. Public orgs are visible to everyone; private orgs
    only show up for their own members.
    """
    user_id = current_user["sub"] if current_user else None

    if mine:
        if not user_id:
            return []
        return query(
            """SELECT o.*, m.role as my_role
               FROM organizations o
               JOIN org_members m ON m.org_id = o.id AND m.user_id = %s::uuid
               ORDER BY o.name ASC""",
            (user_id,),
        )

    return query(
        """SELECT o.*,
                  (SELECT role FROM org_members
                    WHERE org_id = o.id AND user_id = %s::uuid) as my_role
           FROM organizations o
           WHERE o.visibility = 'public'
              OR EXISTS (SELECT 1 FROM org_members m
                          WHERE m.org_id = o.id AND m.user_id = %s::uuid)
           ORDER BY o.member_count DESC, o.created_at DESC""",
        (user_id, user_id),
    )


@router.post("", status_code=201)
def create_org(req: CreateOrgRequest, current_user: dict = Depends(get_current_user)):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Organization name is required")
    if req.visibility not in ("public", "private"):
        raise HTTPException(status_code=400, detail="visibility must be 'public' or 'private'")

    slug = _unique_slug(req.slug or name)

    # Creating the org and its owner membership must happen together —
    # an org with no owner would be unmanageable.
    with get_db() as conn:
        conn.autocommit = False
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """INSERT INTO organizations
                   (slug, name, description, visibility, tags, member_count, created_by)
                   VALUES (%s, %s, %s, %s, %s, 1, %s)
                   RETURNING *""",
                (slug, name, req.description, req.visibility, req.tags, current_user["sub"]),
            )
            org = dict(cur.fetchone())
            cur.execute(
                "INSERT INTO org_members (org_id, user_id, role) VALUES (%s, %s, 'owner')",
                (str(org["id"]), current_user["sub"]),
            )
            conn.commit()
            cur.close()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            raise HTTPException(status_code=409, detail="That organization slug is taken")
        except Exception:
            conn.rollback()
            raise

    org["my_role"] = "owner"
    return org


@router.get("/{slug}")
def get_org(slug: str, current_user: dict = Depends(get_optional_user)):
    org = get_org_or_404(slug)
    user_id = current_user["sub"] if current_user else None
    role = require_read_access(org, user_id)

    org = dict(org)
    org["my_role"] = role
    org["discussion_count"] = (
        query(
            "SELECT COUNT(*) as n FROM discussions WHERE org_id = %s",
            (str(org["id"]),),
            fetch_one=True,
        )
        or {"n": 0}
    )["n"]
    return org


@router.patch("/{slug}")
def update_org(
    slug: str,
    req: UpdateOrgRequest,
    current_user: dict = Depends(get_current_user),
):
    org = get_org_or_404(slug)
    require_role(org, current_user["sub"], "admin")

    if req.visibility is not None and req.visibility not in ("public", "private"):
        raise HTTPException(status_code=400, detail="visibility must be 'public' or 'private'")

    fields = {
        "name": req.name.strip() if req.name is not None else None,
        "description": req.description,
        "avatar_url": req.avatar_url,
        "visibility": req.visibility,
        "tags": req.tags,
    }
    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    params = tuple(updates.values()) + (str(org["id"]),)

    return query_returning(
        f"UPDATE organizations SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING *",
        params,
    )


@router.delete("/{slug}")
def delete_org(slug: str, current_user: dict = Depends(get_current_user)):
    org = get_org_or_404(slug)
    require_role(org, current_user["sub"], "owner")
    execute("DELETE FROM organizations WHERE id = %s", (str(org["id"]),))
    return {"message": "Organization deleted"}


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------


@router.get("/{slug}/members")
def list_members(slug: str, current_user: dict = Depends(get_optional_user)):
    org = get_org_or_404(slug)
    require_read_access(org, current_user["sub"] if current_user else None)

    return query(
        """SELECT u.username, u.display_name, u.avatar_url, m.role, m.joined_at
           FROM org_members m
           JOIN users u ON u.id = m.user_id
           WHERE m.org_id = %s
           ORDER BY CASE m.role
                      WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END,
                    m.joined_at ASC""",
        (str(org["id"]),),
    )


@router.post("/{slug}/join", status_code=201)
def join_org(slug: str, current_user: dict = Depends(get_current_user)):
    org = get_org_or_404(slug)

    if org["visibility"] != "public":
        # Don't confirm the org exists to a non-member.
        raise HTTPException(status_code=404, detail="Organization not found")

    if get_member_role(org["id"], current_user["sub"]):
        raise HTTPException(status_code=409, detail="Already a member")

    execute(
        "INSERT INTO org_members (org_id, user_id, role) VALUES (%s, %s, 'member')",
        (str(org["id"]), current_user["sub"]),
    )
    execute(
        "UPDATE organizations SET member_count = member_count + 1 WHERE id = %s",
        (str(org["id"]),),
    )
    return {"joined": True, "role": "member"}


@router.delete("/{slug}/leave")
def leave_org(slug: str, current_user: dict = Depends(get_current_user)):
    org = get_org_or_404(slug)
    role = require_member(org, current_user["sub"])

    if role == "owner":
        raise HTTPException(
            status_code=400,
            detail="Owners cannot leave. Transfer ownership or delete the organization.",
        )

    execute(
        "DELETE FROM org_members WHERE org_id = %s AND user_id = %s",
        (str(org["id"]), current_user["sub"]),
    )
    execute(
        "UPDATE organizations SET member_count = GREATEST(member_count - 1, 0) WHERE id = %s",
        (str(org["id"]),),
    )
    return {"joined": False}


@router.post("/{slug}/members", status_code=201)
def add_member(
    slug: str,
    req: AddMemberRequest,
    current_user: dict = Depends(get_current_user),
):
    """Invite a user by username. This is how people get into private orgs."""
    org = get_org_or_404(slug)
    actor_role = require_role(org, current_user["sub"], "admin")

    if req.role not in ("member", "admin"):
        raise HTTPException(status_code=400, detail="role must be 'member' or 'admin'")
    if req.role == "admin" and actor_role != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can add admins")

    target = query(
        "SELECT id FROM users WHERE username = %s", (req.username,), fetch_one=True
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if get_member_role(org["id"], str(target["id"])):
        raise HTTPException(status_code=409, detail="User is already a member")

    execute(
        "INSERT INTO org_members (org_id, user_id, role) VALUES (%s, %s, %s)",
        (str(org["id"]), str(target["id"]), req.role),
    )
    execute(
        "UPDATE organizations SET member_count = member_count + 1 WHERE id = %s",
        (str(org["id"]),),
    )
    return {"username": req.username, "role": req.role}


@router.patch("/{slug}/members/{username}")
def update_member_role(
    slug: str,
    username: str,
    req: UpdateMemberRequest,
    current_user: dict = Depends(get_current_user),
):
    org = get_org_or_404(slug)
    require_role(org, current_user["sub"], "owner")

    if req.role not in ("member", "admin"):
        raise HTTPException(status_code=400, detail="role must be 'member' or 'admin'")

    target = query(
        "SELECT id FROM users WHERE username = %s", (username,), fetch_one=True
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target["id"]) == current_user["sub"]:
        raise HTTPException(status_code=400, detail="Cannot change your own owner role")

    updated = query_returning(
        """UPDATE org_members SET role = %s
           WHERE org_id = %s AND user_id = %s
           RETURNING role""",
        (req.role, str(org["id"]), str(target["id"])),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User is not a member")
    return {"username": username, "role": req.role}


@router.delete("/{slug}/members/{username}")
def remove_member(
    slug: str, username: str, current_user: dict = Depends(get_current_user)
):
    org = get_org_or_404(slug)
    actor_role = require_role(org, current_user["sub"], "admin")

    target = query(
        "SELECT id FROM users WHERE username = %s", (username,), fetch_one=True
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target_role = get_member_role(org["id"], str(target["id"]))
    if not target_role:
        raise HTTPException(status_code=404, detail="User is not a member")
    if target_role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the owner")
    if target_role == "admin" and actor_role != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can remove admins")

    execute(
        "DELETE FROM org_members WHERE org_id = %s AND user_id = %s",
        (str(org["id"]), str(target["id"])),
    )
    execute(
        "UPDATE organizations SET member_count = GREATEST(member_count - 1, 0) WHERE id = %s",
        (str(org["id"]),),
    )
    return {"message": "Member removed"}
