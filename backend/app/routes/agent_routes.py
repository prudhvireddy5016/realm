from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ..database import query, query_returning
from ..auth import get_current_user

router = APIRouter(prefix="/api/agents", tags=["agents"])


class CreateAgentRequest(BaseModel):
    name: str
    role: str
    description: Optional[str] = None
    personality: str
    expertise_tags: list[str] = []
    tone: str = "friendly"


@router.get("/")
def list_agents():
    agents = query(
        """SELECT id, name, role, description, avatar_url, expertise_tags, tone,
                  is_community, created_at
           FROM agent_personas
           WHERE is_active = TRUE
           ORDER BY is_community ASC, name ASC"""
    )
    return agents


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    agent = query(
        """SELECT id, name, role, description, avatar_url, expertise_tags, tone,
                  is_community,
                  (SELECT COUNT(*) FROM comments WHERE agent_id = %s) as total_comments
           FROM agent_personas WHERE id = %s""",
        (agent_id, agent_id),
        fetch_one=True,
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/community", status_code=201)
def create_community_agent(
    req: CreateAgentRequest,
    current_user: dict = Depends(get_current_user),
):
    if not req.name or not req.role or not req.personality:
        raise HTTPException(status_code=400, detail="Name, role, and personality required")

    try:
        agent = query_returning(
            """INSERT INTO agent_personas
               (name, role, description, personality, expertise_tags, tone, is_community, created_by)
               VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
               RETURNING id, name, role, description, expertise_tags, tone, is_community""",
            (
                req.name, req.role, req.description, req.personality,
                req.expertise_tags, req.tone, current_user["sub"],
            ),
        )
        return agent
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Agent name already taken")
        raise HTTPException(status_code=500, detail="Server error")
