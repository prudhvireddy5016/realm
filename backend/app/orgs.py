"""
Organization access control
---------------------------
Shared helpers for org membership and permission checks, used by both
org_routes and discussion_routes.

Visibility model:
  - public  : anyone (including logged-out users) can read the org, its
              members, and its discussions. Anyone signed in can join.
  - private : only members can read anything. Joining requires an owner/admin
              to add you.

Roles: owner (the creator, exactly one) > admin > member
"""

import re

from fastapi import HTTPException

from .database import query

ROLE_RANK = {"member": 1, "admin": 2, "owner": 3}


def slugify(name: str) -> str:
    """Turn an org name into a URL-safe slug. Falls back to 'org' if empty."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:50] or "org"


def get_org_or_404(slug: str) -> dict:
    """Fetch an org by slug, or raise 404."""
    org = query("SELECT * FROM organizations WHERE slug = %s", (slug,), fetch_one=True)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def get_member_role(org_id: str, user_id: str | None) -> str | None:
    """Return the user's role in the org, or None if not a member."""
    if not user_id:
        return None
    row = query(
        "SELECT role FROM org_members WHERE org_id = %s AND user_id = %s",
        (str(org_id), user_id),
        fetch_one=True,
    )
    return row["role"] if row else None


def require_read_access(org: dict, user_id: str | None) -> str | None:
    """
    Ensure the user may read this org. Returns their role (None for a
    non-member reading a public org).

    Private orgs 404 rather than 403 for non-members, so their existence
    isn't leaked to outsiders.
    """
    role = get_member_role(org["id"], user_id)
    if org["visibility"] == "private" and role is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return role


def require_member(org: dict, user_id: str) -> str:
    """Ensure the user is a member. Returns their role."""
    role = get_member_role(org["id"], user_id)
    if role is None:
        if org["visibility"] == "private":
            raise HTTPException(status_code=404, detail="Organization not found")
        raise HTTPException(
            status_code=403, detail="You must join this organization first"
        )
    return role


def require_role(org: dict, user_id: str, minimum: str) -> str:
    """Ensure the user's role is at least `minimum` ('admin' or 'owner')."""
    role = require_member(org, user_id)
    if ROLE_RANK[role] < ROLE_RANK[minimum]:
        raise HTTPException(
            status_code=403, detail=f"Requires {minimum} permissions"
        )
    return role
