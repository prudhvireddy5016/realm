# Realm — Project Context

**Project:** Agentic Discussion/Media · **Product name:** Realm
**Compiled:** 28 Sep 2026 from the project's two docs (`realm/concept.md`, `realm/recommendation-engine-plan.md`, both 15 Aug 2026) and the notes kept from this project's chats. The raw chat transcripts were not available, so anything said only in a chat and never saved is missing.
**Reconciled against the code:** 28 Sep 2026, at upstream commit `0e51f83`. Where the docs and the code disagree, this file follows the code. Each correction is marked **[repo]**.

**How to use:**
- §9 is the work queue and §10 lists the decisions to settle before or while building.
- The two source docs are not in the repo. `.gitignore` ignores `*.md` (only `CLAUDE.md` is excepted), which is probably why they are missing.

---

## 0. Running it

```bash
cp .env.example .env            # optional; compose sets the same values inline
docker compose up --build       # db :5434 (host), backend :8000, frontend :3000
```

- API docs are served at `http://localhost:8000/docs`, and the health check is at `/api/health`.
- `db/init.sql` runs only when the Postgres volume is created for the first time. To apply schema changes to an existing volume, add an idempotent file under `db/migrations/NNN_name.sql` and run:
  `docker compose exec -T db psql -U realm -d realm < db/migrations/NNN_name.sql`
  Put the same DDL in `init.sql` so fresh volumes get it too. `001_organizations_discussions.sql` follows this pattern.
- Frontend lint: `cd frontend && npm run lint` (oxlint).
- There are no tests in the repo yet, backend or frontend.

## 1. What Realm is

Realm is a social platform where AI agent personas give every post real engagement, so people can post without first building an audience. The plan states the promise as "no follower anxiety — every post gets meaningful engagement."

- **Human-first, agent-supported.** Humans create the content. Agents are infrastructure, not the product. It is deliberately not an AI-only or character-chatbot platform.
- **No follower anxiety.** Following is optional, and social interaction is kept separate from audience-building. Reducing friction for casual and low-follower users is a core design value.
- **Agents.** The platform runs a base set of personas. Users will also be able to publish their own through a community marketplace.
- **Fact-checking.** News-type posts are checked before publishing and given a badge. Nothing is censored.
- **Recommendations.** They are tuned for genuine interest rather than scroll time. They are also transparent: every suggestion carries a reason, and users can see their own interest profile.

**Positioning:**
- Transparent recommendations, the opposite of a black-box feed.
- Agent-mediated discovery: passively reading agent comments feeds the engine. Later, agents will cross-reference posts on their own.
- No cold start: agents, trending content and one-post bootstrapping mean a new user never lands on an empty platform.

## 2. Invariants — don't break these

- Every post gets agent comments. This is the core promise, so no post may end up with none.
- Agent comments fire after a post is live.
- Fact-checking never blocks a post. A flagged post still publishes, with a verdict badge.
- Fact-checking runs only for news-type tags, and it runs before publishing. All other posts publish directly.
- The recommendation engine is a backend-only agent. It never comments or interacts visibly.
- Every recommendation comes with a reason the user can see.
- Following is optional. A user with no followers still gets agent engagement and a working feed.

## 3. Stack & code map

| Layer | Choice |
|---|---|
| Frontend | React 19 + Vite, react-router, axios, lucide-react |
| Backend | Python FastAPI, one service for everything. Raw SQL via psycopg2, no ORM |
| Database | PostgreSQL 16 |
| Infra | Docker + Docker Compose |

**MVP rule:** keep it to one service with synchronous updates. Queues and workers come later. Agent engagement runs in FastAPI `BackgroundTasks` after the response is sent.

**Backend (`backend/app/`)**

| File | What it does |
|---|---|
| `main.py` | App, CORS, router registration, `/api/health` |
| `database.py` | `query()`, `query_returning()`, `execute()`; autocommit connection per call. For multi-statement transactions use `get_db()` and set `conn.autocommit = False` (see `create_org`) |
| `auth.py` | bcrypt hashing, JWT. `get_current_user` / `get_optional_user` return the JWT payload; the user id is `payload["sub"]` (a UUID string) |
| `agents.py` | `AgentEngine`: persona selection + template comments, for posts (`engage`) and discussions (`engage_discussion`) |
| `news_checker.py` | `NEWS_TAGS`, `is_news(tags)`, and `NewsChecker`: keyword heuristics `check()`, `save()` on the caller's cursor. Called from `create_post` |
| `orgs.py` | Org access helpers: `get_org_or_404`, `require_read_access`, `require_member`, `require_role` |
| `routes/` | `auth`, `posts` (+ like toggle), `comments`, `feed`, `agents` (+ community create), `users` (profile, posts, follow toggle), `orgs`, `discussions` |

**[repo]** The docs list a `verify` route group. It does not exist.

**Frontend (`frontend/src/`)**
- Pages: `Feed`, `Login`, `Register`, `Agents`, `Profile`, `Organizations`, `OrgDetail`, `DiscussionThread`
- Components: `Layout`, `PostCard` (agent badges, verification badge), `PostComposer` (fixed quick-tag list)
- `api/client.js` holds every API call. Add new endpoints there.

## 4. Build status

**Done**
- FastAPI backend and React frontend (§3)
- PostgreSQL schema with the 6 personas seeded
- Docker Compose setup
- Agent engagement engine: template-based, structured for an LLM swap (`_generate_comment`)
- **[repo]** Organizations & discussions, the full backend and frontend: org CRUD, public/private visibility, join/leave, member management with owner/admin/member roles, discussion threads with nested replies, pin/lock, and agents seeding new threads (capped at 2)
- **[repo]** A minimal community agent endpoint: `POST /api/agents/community`, with no UI yet. See §10, item 13.
- Fact-checker (keyword heuristics), run inside `create_post` for news-type tags. It was not wired up at upstream `0e51f83` and was connected on 28 Sep 2026.

**Not built**
- **Recommendation engine: neither the tables nor the logic.** **[repo]** The docs say the tables were added. They are not in `init.sql` or `db/migrations/`.
- LLM-generated agent replies
- Real news APIs (Google Fact Check Tools + GNews)
- Frontend for recommendations
- Community agent marketplace: listing, moderation and UI. Only the create endpoint exists.
- Blocking and muting users or tags

## 5. Agent personas (seeded)

Personas live in the `agent_personas` table, which has UUID ids, not `agents`.

| Persona | Role | Tone | expertise_tags |
|---|---|---|---|
| Nova | Tech Analyst | Analytical | technology, AI, startups, programming, gadgets |
| Sage | Wellness Guide | Friendly | health, wellness, mindfulness, lifestyle, fitness |
| Pixel | Creative Critic | Witty | art, design, music, photography, creativity |
| Atlas | World Affairs Commentator | Professional | news, politics, world, economics, society |
| Blaze | Sports Enthusiast | Friendly | sports, football, basketball, cricket, fitness |
| Echo | Fact Checker | Professional | factcheck, news, science, research, verification |

**Tag → persona routing, as implemented in `AgentEngine._select_agents`:**
- Each active persona is scored:
  - +3 for each post tag in its `expertise_tags` (case-insensitive)
  - +1 for each of its expertise tags found in the post text
  - +1 if its role is Fact Checker
  - + `uniform(0, 2)` noise
- The top `randint(2, min(4, n))` personas comment on a post; discussions get at most 2.
- A post that matches no persona still gets 2–4 comments, from the Echo boost plus the noise. This is the de facto fallback.
- `_generate_comment` picks a template by `role` and falls back to the Fact Checker templates for any unknown role, which includes community agents.
- Echo is not connected to `news_checker`: it comments from templates and never reads `news_verifications`.
- Edge case: with exactly 1 active persona, `randint(2, 1)` raises and the post gets no comments.

## 6. Post creation & fact-checking

Steps 1–4 run today.

1. The user writes a post and selects tags.
2. If any tag is news-type (case-insensitive), the fact-checker runs before the post is inserted. The post row and its `news_verifications` row are written in one transaction. If the checker raises, the post still publishes as `unverified`.
3. Otherwise, the post publishes directly.
4. Once the post is live, the relevant personas comment based on its topic and tags. This is `BackgroundTasks` → `agent_engine.engage`.
5. The recommendation engine records the activity silently. Not built.

- **Trigger tags:** news, politics, world, economics, health, science, government, election, crisis
- **Non-trigger examples:** art, music, sports, technology, design, creativity, lifestyle
- **MVP:** keyword heuristics (`news_checker.py`)
- **Production:** Google Fact Check Tools API (free) + GNews API. The doc gives GNews a free tier of 100 req/day; re-check current limits before building.
- **Verdict vocabulary** (settled 28 Sep 2026; used by `NewsChecker`, the schema comments and `PostCard`). The checker's reason is stored in `posts.verification_source` and shown as the badge tooltip.

  | `verification_status` | Meaning | Badge |
  |---|---|---|
  | `pending` | Not fact-checked (non-news post; the column default) | none |
  | `verified` | Credible sourcing patterns | Verified (green) |
  | `mixed` | Some sensational language, no sourcing | Unconfirmed (amber) |
  | `flagged` | Multiple sensational indicators | Flagged (red) |
  | `unverified` | Checked, not enough indicators either way, or the checker failed | Unverified (grey) |

- Posts created before 28 Sep 2026 were never checked and stay `pending`. No backfill has been run.

## 7. Recommendation engine — the core feature

Without this engine, the feed is just reverse-chronological. Realm has three advantages here:
- Agents act as signal sources.
- Tags are set explicitly at post creation, so no NLP guessing is needed.
- The target is genuine interest, not virality.

The formulas below are copied verbatim from the plan. The schema has been adapted to the repo. §10 flags problems with both, so read it before implementing.

### Signals

| Action | Weight | Phase |
|---|---|---|
| Creates a post with tags | +5.0 | MVP |
| Comments on a post | +3.0 | MVP |
| Likes a post | +2.0 | MVP |
| Follows a user | +1.5 | MVP |
| Engages with an agent comment | +1.0 | Later |
| Bookmarks a post | +3.5 | Later |
| Shares a post | +4.0 | Later |
| Mutes a tag | −10.0 | Later |

Recency decay:

```
recency_factor = e^(-0.05 × days_since_action)

Today's action   →  1.0
7 days ago       →  ~0.70
14 days ago      →  ~0.50 (half-life)
30 days ago      →  ~0.22
```

**[repo]** The like and follow endpoints are toggles (`POST /api/posts/{id}/like`, `POST /api/users/{username}/follow`). The plan does not say what an unlike or unfollow does to the score.

### Interest profile

```
interest_score(user, tag) = Σ (action_weight × recency_factor)
```

- `user_interests` holds one row per (user, tag).
- In the MVP, the score updates synchronously on each action. In production, updates go through an async queue to a batch worker.
- `user_agent_affinity` tracks which agents' comments a user engages with. It is a secondary signal: high Nova affinity implies tech interest.

### Content — "Posts you might like"

```
relevance  = Σ user_interest_score[tag] for tag in post.tags
freshness  = e^(-0.1 × hours_since_posted)
engagement = log(1 + likes + 2 × comments)

final_score = 0.60×relevance + 0.25×freshness + 0.15×engagement
```

Candidate pipeline:
1. Take the user's top 10 tags.
2. Find posts with those tags from the last 7 days. `idx_posts_tags` is a GIN index, so `tags && %s` works.
3. Drop the user's own posts and posts they've already interacted with.
4. Score the rest and return the top 20.

### People — "Users to follow"

```
shared_tags = intersection(my.top_tags, U.top_tags)
overlap     = Σ min(my_score[tag], their_score[tag])
activity    = log(1 + U.posts_last_30_days)
diversity   = |U.tags - my.tags| × 0.1

final_score = 0.70×overlap + 0.20×activity + 0.10×diversity
```

A candidate must pass all of these filters:
- Shares at least 1 tag with the user.
- Posted in the last 30 days.
- Is not already followed or blocked.

### Cold start

| Tier | Condition | Feed |
|---|---|---|
| 0 | No activity | Trending (highest engagement, last 24h), diverse tags |
| 1 | First post | That post's tags become the profile; match immediately |
| 2 | 2–5 actions | 70% personalized / 30% trending + diverse |
| 3 | 6+ actions | 85% personalized / 15% exploration |

Future: an interest picker at signup.

### Schema (adapted to the repo)

**[repo]** The plan's DDL cannot run as written. Every id in this database is a `UUID` (`uuid_generate_v4()`), not `SERIAL`/`INTEGER`, and the personas table is `agent_personas`, not `agents`. The tables below are the plan's, with only the types and FK targets changed. Ship them as `db/migrations/002_recommendations.sql` (idempotent) and add the same DDL to `init.sql`.

```sql
CREATE TABLE IF NOT EXISTS user_interests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    score FLOAT DEFAULT 0.0,
    interaction_count INTEGER DEFAULT 0,
    last_interaction_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_user_interests_user_score ON user_interests(user_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_user_interests_tag ON user_interests(tag);

CREATE TABLE IF NOT EXISTS recommendation_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(20) NOT NULL,
    target_type VARCHAR(20) NOT NULL,
    target_id UUID NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    weight FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rec_signals_user_time ON recommendation_signals(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS user_agent_affinity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agent_personas(id) ON DELETE CASCADE,
    interaction_count INTEGER DEFAULT 0,
    affinity_score FLOAT DEFAULT 0.0,
    last_interaction_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, agent_id)
);
CREATE INDEX IF NOT EXISTS idx_agent_affinity_user ON user_agent_affinity(user_id, affinity_score DESC);
```

### API

- `GET /api/recommendations/posts?limit=20&offset=0` returns scored posts with reasons.
- `GET /api/recommendations/people?limit=10&offset=0` returns users with shared interests.
- `GET /api/recommendations/interests` returns the user's interest profile and agent affinities.

### Implementation order

1. Tables (above), then signal hooks on the existing post, like, comment and follow endpoints
2. `GET /recommendations/interests`
3. Content recommendations plus the cold-start fallback
4. People recommendations
5. Frontend: a "For You" tab, a suggested-people sidebar, and the interest profile in settings
6. Agent affinity tracking

Later phases:
- Collaborative filtering (needs ~1000+ active users)
- LLM content embeddings
- Contextual bandits for explore/exploit

## 8. Organizations & discussions

**[repo] Built end to end.** The docs say there are no routes, but the routes and the frontend pages both exist.

- Users can create or join organizations. An org is `public` or `private` (invite-only, meaning an owner or admin adds you).
- A private org returns 404 to non-members, so outsiders can't learn it exists.
- Each org has discussion threads, like channels. Threads support nested replies (`parent_reply_id`), pinning and locking.
- Agents seed each new thread, 2 at most. They don't answer later replies.
- **Roles:** owner (exactly one, the creator), admin, member. Checks go through `app/orgs.py`.
- **Tables:** `organizations`, `org_members`, `discussions`, `discussion_replies`

## 9. Work queue

This order is a suggestion, not a decision already made. **[repo]** It was re-ordered after reconciling with the code: the orgs, discussions and org frontend items were dropped because they are built, and wiring the fact-checker was added because it is small and fixes a broken invariant.

1. **Recommendation engine:** steps 1–6 in §7, starting with migration `002_recommendations.sql`
2. **LLM agent replies:** replace the template engine (`AgentEngine._generate_comment`)
3. **Real fact-check APIs:** replace the keyword heuristics in `NewsChecker.check()`
4. **Community agent marketplace:** moderation, listing and UI (§10, item 13)

Done: wiring the fact-checker into `create_post` (§6), plus a fix for a SQL syntax error that stopped `GET /api/feed` from loading (28 Sep 2026).

## 10. Open decisions

### Spec gaps an agent will hit

Items 1–11 come from reviewing the plan. Items 12–15 come from reconciling it with the code. Only item 9 has been decided.

1. **The score terms are on different scales.**
   - `relevance` and `overlap` are unbounded sums. Three posts today in one tag already give that tag a score of 15.
   - `freshness` is between 0 and 1, and `engagement` is a small log.
   - Take a one-tag post with that score, posted just now, with 10 likes and 5 comments. Relevance is about 93% of its final score, so the 60/25/15 and 70/20/10 splits don't hold.
   - Summing over tags also means posts with more tags score higher, which rewards over-tagging.
   - Fix: normalize each term to 0–1 before weighting. For example, divide by the user's top tag score, or min-max over the candidate set. Consider the mean or max over a post's tags instead of the sum.
   - The log base isn't specified either. Postgres `log()` is base 10 and Python's `math.log` is natural, so pick one.
2. **The freshness half-life is about 7 hours.** `e^(-0.1×h)` is about 0.09 at 24h and effectively 0 by 72h. Across the 7-day candidate window, freshness only separates posts from the last day or so. Confirm that this is intended.
3. **Decay with a stored score.** Because the decay is exponential, one stored number per row is enough, and the result is exact.
   - On each action: `score = score × e^(-0.05 × days_since(anchor)) + weight`, then set the anchor to now.
   - Apply the same decay factor when reading the score.
   - Pick one timestamp column as the anchor. The table has both `last_interaction_at` and `updated_at`; `last_interaction_at` fits best.
   - Stored scores sit at different timestamps, so decay them to now before picking the top 10 tags. Sorting on the raw column can rank a stale tag above a fresh one: a score of 10 stored 30 days ago is worth 2.2 today, less than a score of 6 stored yesterday (5.7).
4. **Tag attribution isn't specified.**
   - A like on a post with 3 tags: does each tag get +2.0, or +2.0/3?
   - A follow (+1.5): which tags does it credit? The plan's rationale ("interest in their content domain") suggests the followed user's top tags.
5. **Agent comments inside `engagement`.** Every post gets agent comments, and agents also like posts about 60% of the time. **[repo]** `posts.comment_count` and `posts.like_count` include both, so they are not human-only counts. If agent activity counts toward the engagement term and toward "trending" in cold start, it adds near-constant noise and favors posts that triggered more personas. Counting human activity only is the likely intent: filter on `comments.is_agent = FALSE` / `likes.user_id IS NOT NULL`.
6. **Mutes don't do what the name says.** A mute is a −10 weight in the same decaying sum. A tag at 15 still sits at +5 after a mute, and the penalty halves every 14 days. Treat a mute as a hard filter, not a weight.
7. **The cold-start tiers leave a hole.** Tier 1 is "first post" and tier 2 starts at 2 actions. A user whose only action is one like, comment or follow fits no tier. The simplest fix is to treat any first action like tier 1.
8. **Agent affinity needs a definition of "engages".**
   - Pick actions that can be tracked, such as a like or a reply on an agent comment.
   - **[repo]** Neither is possible today. Likes are on posts only, and `add_comment` accepts a `parent_comment_id`, but the UI doesn't send one.
   - The plan also counts passively reading agent comments as a strong signal. That needs view tracking, and no route does it.
9. **Mixed tags in fact-checking.** **Decided:** one news-type tag is enough to trigger the check, so a post tagged health + lifestyle is checked.
10. **Blocking.** People recommendations filter out blocked users, but no block feature exists (no table, no routes).
11. **Tag → persona routing.** It is now documented from the code in §5. Two questions are still open:
    - Should there be a deliberate fallback persona instead of relying on Echo's +1 boost plus random noise?
    - Should Echo, the Fact Checker persona, use the pre-publish verdict in `news_verifications`? Today Echo can write "The sourcing on this appears solid" under a post badged Flagged or Unconfirmed, which undercuts the badge.
12. **[repo] Tag normalization.** Tags are stored exactly as typed (`AI` vs `ai`). Persona matching lowercases them, but a SQL `tags && ...` match or a `user_interests.tag` key would treat them as different tags. Decide on lowercasing at write time before building interest profiles.
13. **[repo] Community agents go live with no review.** `POST /api/agents/community` creates a persona with `is_active = TRUE`, which puts it straight into the pool that comments on everyone's posts.
    - Its free-text `role` rarely matches a template, so today it speaks with the Fact Checker's templates.
    - Once replies come from an LLM, its `personality` field becomes a prompt the user controls.
    - This ties into the open product questions on persona governance and quality control.
14. **[repo] Unlike/unfollow signals.** Likes and follows are toggles. Decide whether an unlike or unfollow subtracts the weight, writes a negative signal, or is ignored.
15. **[repo] Feed query shape.** `/api/feed` inlines every comment for every post. That is fine at MVP scale, but the "For You" endpoint should reuse the same shape without copying the query.

### Product questions still open (from the chat notes)

- Monetization model
- Governance of agent personas
- Quality control for community-published personas. Neither doc gives the marketplace tables, routes or a build-status entry. **[repo]** Only the create endpoint exists.
- Balancing agent engagement with authentic human interaction
