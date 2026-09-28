-- ===========================================================================
-- Migration 001: Organizations & Discussions
-- ---------------------------------------------------------------------------
-- db/init.sql only runs when the postgres volume is first created, so apply
-- this against an already-running database:
--
--   docker compose exec -T db psql -U realm -d realm \
--     < db/migrations/001_organizations_discussions.sql
--
-- Idempotent — safe to re-run.
-- ===========================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ORGANIZATIONS
-- Public orgs are readable/joinable by anyone.
-- Private orgs are readable only by members; joining requires an invite
-- from an owner/admin.
-- ============================================
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    avatar_url TEXT,
    visibility VARCHAR(10) NOT NULL DEFAULT 'public',
    tags TEXT[] DEFAULT '{}',
    member_count INTEGER NOT NULL DEFAULT 0,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT org_visibility_check CHECK (visibility IN ('public', 'private'))
);

-- ============================================
-- ORG MEMBERSHIP
-- Roles: owner (exactly one, the creator), admin, member
-- ============================================
CREATE TABLE IF NOT EXISTS org_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_org_member UNIQUE (org_id, user_id),
    CONSTRAINT org_role_check CHECK (role IN ('owner', 'admin', 'member'))
);

-- ============================================
-- DISCUSSIONS (threads within an org, like channels)
-- ============================================
CREATE TABLE IF NOT EXISTS discussions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    body TEXT,
    tags TEXT[] DEFAULT '{}',
    is_pinned BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    reply_count INTEGER NOT NULL DEFAULT 0,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- DISCUSSION REPLIES (nested; from humans and agents)
-- Mirrors the comments table author model: exactly one of user_id/agent_id.
-- ============================================
CREATE TABLE IF NOT EXISTS discussion_replies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discussion_id UUID NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
    parent_reply_id UUID REFERENCES discussion_replies(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agent_personas(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_agent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT reply_author_check CHECK (
        (user_id IS NOT NULL AND agent_id IS NULL AND is_agent = FALSE) OR
        (user_id IS NULL AND agent_id IS NOT NULL AND is_agent = TRUE)
    )
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_org_members_org ON org_members(org_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);
CREATE INDEX IF NOT EXISTS idx_orgs_visibility ON organizations(visibility);
CREATE INDEX IF NOT EXISTS idx_orgs_tags ON organizations USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_discussions_org ON discussions(org_id);
CREATE INDEX IF NOT EXISTS idx_discussions_activity ON discussions(org_id, last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_replies_discussion ON discussion_replies(discussion_id);
CREATE INDEX IF NOT EXISTS idx_replies_parent ON discussion_replies(parent_reply_id);
