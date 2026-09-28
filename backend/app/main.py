"""
Realm Backend
-------------
Python FastAPI backend for the Realm social platform.
Handles auth, posts, feed, comments, agents, users, and news verification.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.auth_routes import router as auth_router
from .routes.post_routes import router as post_router
from .routes.comment_routes import router as comment_router
from .routes.feed_routes import router as feed_router
from .routes.agent_routes import router as agent_router
from .routes.user_routes import router as user_router
from .routes.org_routes import router as org_router
from .routes.discussion_routes import router as discussion_router

app = FastAPI(
    title="Realm API",
    description="Social platform with AI agent engagement",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes
app.include_router(auth_router)
app.include_router(post_router)
app.include_router(comment_router)
app.include_router(feed_router)
app.include_router(agent_router)
app.include_router(user_router)
app.include_router(org_router)
app.include_router(discussion_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "realm-backend", "stack": "python-fastapi"}


@app.on_event("startup")
def startup():
    print("🌐 Realm Backend (Python/FastAPI) starting...")


@app.on_event("shutdown")
def shutdown():
    print("Realm Backend shutting down.")
