"""
Realm Agent Engine
------------------
Selects relevant agent personas based on post content/tags and generates
contextual comments. For MVP, uses template-based responses.
In production, swap _generate_comment() to call an LLM API (Claude, etc.)
"""

import random
import time
from .database import get_db
import psycopg2.extras


# ---------------------------------------------------------------------------
# Template responses by agent role (MVP — replace with LLM calls in prod)
# ---------------------------------------------------------------------------
RESPONSE_TEMPLATES = {
    "Tech Analyst": [
        "Interesting take on this. The tech landscape is shifting fast — {topic_note}. Worth watching how this plays out.",
        "From a technical standpoint, this raises some solid points. {topic_note} The data supports a measured approach here.",
        "This aligns with what we're seeing in the industry. {topic_note} Curious to see how adoption trends evolve.",
        "Good observation. {topic_note} The underlying technology here has real potential if scaled properly.",
    ],
    "Wellness Guide": [
        "This is a great reminder to stay mindful about {topic_note}. Balance is everything.",
        "Love seeing this kind of content. {topic_note} Taking care of ourselves is the foundation for everything else.",
        "Really thoughtful post. {topic_note} It's important we have these conversations openly.",
        "Thanks for sharing this perspective. {topic_note} Small positive changes compound over time.",
    ],
    "Creative Critic": [
        "The creative energy here is fantastic! {topic_note} Would love to see this concept pushed even further.",
        "Now THIS is what I'm talking about. {topic_note} The execution really sells it.",
        "Bold choice — and it works. {topic_note} Keep experimenting, this direction has legs.",
        "Really appreciate the originality here. {topic_note} Not enough people take creative risks like this.",
    ],
    "World Affairs Commentator": [
        "Important context to consider here: {topic_note}. This connects to broader global trends worth following.",
        "This is a significant development. {topic_note} The implications extend beyond what's immediately obvious.",
        "Good to see attention on this topic. {topic_note} Multiple perspectives are needed to understand the full picture.",
        "Timely post. {topic_note} History shows us that these patterns tend to have lasting consequences.",
    ],
    "Sports Enthusiast": [
        "Great call! {topic_note} The stats back this up when you look at recent performance data.",
        "This is what makes sports so exciting! {topic_note} You can never fully predict what'll happen next.",
        "Solid analysis! {topic_note} The momentum shift has been real and the numbers show it.",
        "Love the passion in this post! {topic_note} True fans know these details matter.",
    ],
    "Fact Checker": [
        "I looked into this — {topic_note}. Always good to verify before sharing widely.",
        "Quick fact check: {topic_note}. The sourcing on this appears solid from what I can see.",
        "Worth noting some additional context here: {topic_note}. Accuracy matters, especially on topics like this.",
        "Checked against available sources — {topic_note}. Encouraging everyone to verify claims independently too.",
    ],
}

TOPIC_NOTES = {
    "technology": "the pace of innovation in this space is unprecedented",
    "AI": "AI capabilities are evolving faster than most predictions suggested",
    "startups": "the startup ecosystem is always full of surprises",
    "programming": "clean architecture makes all the difference long-term",
    "health": "prioritizing health is always a smart investment",
    "wellness": "mental and physical wellness go hand in hand",
    "art": "art that challenges perspective is art that matters",
    "design": "good design is invisible — you only notice bad design",
    "music": "music has this incredible power to connect people",
    "news": "staying informed while filtering noise is a real skill",
    "politics": "nuanced understanding beats hot takes every time",
    "sports": "the competition this season has been absolutely fierce",
    "fitness": "consistency beats intensity every single time",
    "default": "there's a lot to unpack here and it's worth the discussion",
}


class AgentEngine:
    """Handles selecting agents and generating engagement for posts."""

    def _select_agents(self, content: str, tags: list[str]) -> list[dict]:
        """Select 2-4 relevant agent personas based on post content and tags."""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM agent_personas WHERE is_active = TRUE")
            all_agents = cur.fetchall()
            cur.close()

        if not all_agents:
            return []

        content_lower = content.lower()
        scored = []

        for agent in all_agents:
            score = 0
            agent_tags = agent.get("expertise_tags") or []

            # Tag overlap
            for tag in tags:
                if tag.lower() in [t.lower() for t in agent_tags]:
                    score += 3

            # Content keyword overlap
            for tag in agent_tags:
                if tag.lower() in content_lower:
                    score += 1

            # Fact Checker always gets a small boost
            if agent["role"] == "Fact Checker":
                score += 1

            # Randomness so it's not always the same agents
            score += random.uniform(0, 2)
            scored.append((dict(agent), score))

        scored.sort(key=lambda x: x[1], reverse=True)
        num_agents = random.randint(2, min(4, len(scored)))
        return [agent for agent, _ in scored[:num_agents]]

    def _generate_comment(self, agent: dict, content: str, tags: list[str]) -> str:
        """
        Generate a contextual comment for an agent persona.
        MVP: template-based. Production: call LLM with agent personality prompt.
        """
        role = agent["role"]
        templates = RESPONSE_TEMPLATES.get(role, RESPONSE_TEMPLATES["Fact Checker"])
        template = random.choice(templates)

        # Find best topic note
        topic_note = TOPIC_NOTES["default"]
        for tag in tags:
            if tag.lower() in TOPIC_NOTES:
                topic_note = TOPIC_NOTES[tag.lower()]
                break

        if topic_note == TOPIC_NOTES["default"]:
            for keyword, note in TOPIC_NOTES.items():
                if keyword != "default" and keyword in content.lower():
                    topic_note = note
                    break

        return template.format(topic_note=topic_note)

    def engage(self, post_id: str, content: str, tags: list[str]):
        """
        Main engagement function. Called in background when a post is created.
        Selects agents, generates comments, saves to database.
        """
        # Small delay to simulate natural engagement timing
        time.sleep(random.uniform(1, 3))

        selected_agents = self._select_agents(content, tags)

        with get_db() as conn:
            cur = conn.cursor()

            for i, agent in enumerate(selected_agents):
                if i > 0:
                    time.sleep(random.uniform(0.5, 2))

                comment_text = self._generate_comment(agent, content, tags)

                cur.execute(
                    """INSERT INTO comments (post_id, agent_id, content, is_agent)
                       VALUES (%s, %s, %s, TRUE)""",
                    (post_id, str(agent["id"]), comment_text),
                )

                cur.execute(
                    "UPDATE posts SET comment_count = comment_count + 1 WHERE id = %s",
                    (post_id,),
                )

                # Some agents might also like the post
                if random.random() > 0.4:
                    try:
                        cur.execute(
                            "INSERT INTO likes (post_id, agent_id) VALUES (%s, %s)",
                            (post_id, str(agent["id"])),
                        )
                        cur.execute(
                            "UPDATE posts SET like_count = like_count + 1 WHERE id = %s",
                            (post_id,),
                        )
                    except Exception:
                        pass  # Duplicate like, ignore

            cur.close()

        print(f"✅ {len(selected_agents)} agents engaged with post {post_id}")

    def engage_discussion(self, discussion_id: str, title: str, body: str, tags: list[str]):
        """
        Agent engagement for org discussion threads. Called in the background
        when a discussion is created.

        Same selection/generation path as posts, but capped at 2 agents —
        a thread is meant to be driven by its members, with agents seeding
        the conversation rather than dominating it.
        """
        time.sleep(random.uniform(1, 3))

        content = f"{title}\n{body}".strip()
        selected_agents = self._select_agents(content, tags)[:2]

        with get_db() as conn:
            cur = conn.cursor()

            for i, agent in enumerate(selected_agents):
                if i > 0:
                    time.sleep(random.uniform(0.5, 2))

                reply_text = self._generate_comment(agent, content, tags)

                cur.execute(
                    """INSERT INTO discussion_replies
                       (discussion_id, agent_id, content, is_agent)
                       VALUES (%s, %s, %s, TRUE)""",
                    (discussion_id, str(agent["id"]), reply_text),
                )

                cur.execute(
                    """UPDATE discussions
                       SET reply_count = reply_count + 1, last_activity_at = NOW()
                       WHERE id = %s""",
                    (discussion_id,),
                )

            cur.close()

        print(f"✅ {len(selected_agents)} agents joined discussion {discussion_id}")


# Singleton instance used across the app
agent_engine = AgentEngine()
