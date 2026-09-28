from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..database import query, query_returning
from ..auth import hash_password, verify_password, create_token, get_current_user
from fastapi import Depends

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=201)
def register(req: RegisterRequest):
    # Check if user exists
    existing = query(
        "SELECT id FROM users WHERE username = %s OR email = %s",
        (req.username, req.email),
    )
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already taken")

    password_hash = hash_password(req.password)
    user = query_returning(
        """INSERT INTO users (username, email, password_hash, display_name)
           VALUES (%s, %s, %s, %s)
           RETURNING id, username, email, display_name, avatar_url, bio, created_at""",
        (req.username, req.email, password_hash, req.display_name or req.username),
    )

    token = create_token(str(user["id"]), user["username"])
    return {"user": user, "token": token}


@router.post("/login")
def login(req: LoginRequest):
    users = query("SELECT * FROM users WHERE email = %s", (req.email,))
    if not users:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = users[0]
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(str(user["id"]), user["username"])
    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "display_name": user["display_name"],
            "avatar_url": user["avatar_url"],
            "bio": user["bio"],
            "created_at": user["created_at"],
        },
        "token": token,
    }


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    user = query(
        """SELECT id, username, email, display_name, avatar_url, bio, created_at
           FROM users WHERE id = %s""",
        (current_user["sub"],),
        fetch_one=True,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
