-- Realm Database Schema
-- A social platform with AI agent engagement

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(30) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    avatar_url TEXT,
    bio TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- AGENT PERSONAS
-- Deployed by the platform, not by users
-- ============================================
CREATE TABLE agent_personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    role VARCHAR(100) NOT NULL,          -- e.g. "Tech Analyst", "Creative Critic"
    description TEXT,
    avatar_url TEXT,
    personality TEXT NOT NULL,            -- personality description for generating responses
    expertise_tags TEXT[] DEFAULT '{}',   -- topics this agent specializes in
    tone VARCHAR(30) DEFAULT 'friendly', -- friendly, professional, witty, analytical
    is_active BOOLEAN DEFAULT TRUE,
    is_community BOOLEAN DEFAULT FALSE,  -- true if published by a community user
    created_by UUID REFERENCES users(id),-- null for platform agents, user_id for community
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- POSTS
-- ============================================
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    media_url TEXT,
    media_type VARCHAR(20),              -- image, video, link
    tags TEXT[] DEFAULT '{}',
    verification_status VARCHAR(20) DEFAULT 'pending', -- pending (not checked), verified, mixed, flagged, unverified
    verification_source TEXT,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- COMMENTS (from both humans and agents)
-- ============================================
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agent_personas(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_agent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT comment_author_check CHECK (
        (user_id IS NOT NULL AND agent_id IS NULL AND is_agent = FALSE) OR
        (user_id IS NULL AND agent_id IS NOT NULL AND is_agent = TRUE)
    )
);

-- ============================================
-- LIKES (from both humans and agents)
-- ============================================
CREATE TABLE likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agent_personas(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT like_author_check CHECK (
        (user_id IS NOT NULL AND agent_id IS NULL) OR
        (user_id IS NULL AND agent_id IS NOT NULL)
    ),
    CONSTRAINT unique_user_like UNIQUE (post_id, user_id),
    CONSTRAINT unique_agent_like UNIQUE (post_id, agent_id)
);

-- ============================================
-- FOLLOWS (optional - users can follow others)
-- ============================================
CREATE TABLE follows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_follow UNIQUE (follower_id, following_id),
    CONSTRAINT no_self_follow CHECK (follower_id != following_id)
);

-- ============================================
-- NEWS VERIFICATION CACHE
-- ============================================
CREATE TABLE news_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    claim_text TEXT,
    verdict VARCHAR(20) NOT NULL,       -- verified, mixed, flagged, unverified
    confidence FLOAT,
    sources JSONB DEFAULT '[]',
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_posts_tags ON posts USING GIN(tags);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_agent_id ON comments(agent_id);
CREATE INDEX idx_likes_post_id ON likes(post_id);
CREATE INDEX idx_follows_follower ON follows(follower_id);
CREATE INDEX idx_follows_following ON follows(following_id);
CREATE INDEX idx_agent_expertise ON agent_personas USING GIN(expertise_tags);

-- ============================================
-- SEED: Default Agent Personas
-- ============================================
INSERT INTO agent_personas (name, role, description, personality, expertise_tags, tone, avatar_url) VALUES
(
    'Nova',
    'Tech Analyst',
    'A sharp tech industry analyst who breaks down technical topics and trends.',
    'You are Nova, a tech analyst on Realm. You provide insightful, data-driven commentary on technology posts. You reference real trends and give balanced takes. Keep responses concise (2-3 sentences). Be helpful but not preachy.',
    ARRAY['technology', 'AI', 'startups', 'programming', 'gadgets'],
    'analytical',
    '/avatars/nova.png'
),
(
    'Sage',
    'Wellness Guide',
    'A thoughtful wellness advocate who promotes healthy discussions and balanced perspectives.',
    'You are Sage, a wellness guide on Realm. You bring a calm, supportive perspective to conversations. You encourage healthy dialogue and offer balanced viewpoints. Keep responses warm and concise (2-3 sentences).',
    ARRAY['health', 'wellness', 'mindfulness', 'lifestyle', 'fitness'],
    'friendly',
    '/avatars/sage.png'
),
(
    'Pixel',
    'Creative Critic',
    'An enthusiastic creative who appreciates art, design, music, and all forms of expression.',
    'You are Pixel, a creative critic on Realm. You appreciate creativity and offer constructive feedback on artistic content. You are enthusiastic but also give honest, thoughtful critiques. Keep responses expressive and concise (2-3 sentences).',
    ARRAY['art', 'design', 'music', 'photography', 'creativity'],
    'witty',
    '/avatars/pixel.png'
),
(
    'Atlas',
    'World Affairs Commentator',
    'A knowledgeable commentator on global events, politics, and social issues.',
    'You are Atlas, a world affairs commentator on Realm. You provide factual, balanced commentary on news and global events. You cite context and avoid bias. Keep responses informative and concise (2-3 sentences). Flag potential misinformation politely.',
    ARRAY['news', 'politics', 'world', 'economics', 'society'],
    'professional',
    '/avatars/atlas.png'
),
(
    'Blaze',
    'Sports Enthusiast',
    'A passionate sports fan who lives and breathes competition, stats, and highlights.',
    'You are Blaze, a sports enthusiast on Realm. You bring energy and stats knowledge to sports discussions. You celebrate great plays and offer tactical analysis. Keep responses enthusiastic and concise (2-3 sentences).',
    ARRAY['sports', 'football', 'basketball', 'cricket', 'fitness'],
    'friendly',
    '/avatars/blaze.png'
),
(
    'Echo',
    'Fact Checker',
    'A dedicated fact-checker who helps verify claims and combat misinformation.',
    'You are Echo, a fact-checker on Realm. Your primary job is to verify claims in posts. When you spot potential misinformation, flag it politely with sources. When content is accurate, affirm it. Always be respectful. Keep responses factual and concise (2-3 sentences).',
    ARRAY['factcheck', 'news', 'science', 'research', 'verification'],
    'professional',
    '/avatars/echo.png'
);

-- Seed a demo user
INSERT INTO users (username, email, password_hash, display_name, bio) VALUES
('demo', 'demo@realm.social', '$2b$10$placeholder_hash_replace_on_signup', 'Demo User', 'Just exploring Realm!');

-- ============================================
-- ORGANIZATIONS
-- Public orgs are readable/joinable by anyone.
-- Private orgs are readable only by members; joining requires an invite
-- from an owner/admin.
-- ============================================
CREATE TABLE organizations (
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
CREATE TABLE org_members (
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
CREATE TABLE discussions (
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
CREATE TABLE discussion_replies (
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

CREATE INDEX idx_org_members_org ON org_members(org_id);
CREATE INDEX idx_org_members_user ON org_members(user_id);
CREATE INDEX idx_orgs_visibility ON organizations(visibility);
CREATE INDEX idx_orgs_tags ON organizations USING GIN(tags);
CREATE INDEX idx_discussions_org ON discussions(org_id);
CREATE INDEX idx_discussions_activity ON discussions(org_id, last_activity_at DESC);
CREATE INDEX idx_replies_discussion ON discussion_replies(discussion_id);
CREATE INDEX idx_replies_parent ON discussion_replies(parent_reply_id);
