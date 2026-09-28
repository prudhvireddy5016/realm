"""
News Checker
-------------
Fake news detection for Realm posts.
MVP: heuristic-based keyword analysis.
Production: integrate with Google Fact Check API, NewsAPI, ClaimBuster, etc.

Runs before a post is published, and only when at least one of its tags is
news-type. It never blocks a post: every verdict still publishes, with a badge.

posts.verification_status vocabulary:
  pending     not fact-checked (non-news post; the column default). No badge.
  verified    credible sourcing patterns
  mixed       some sensational language, no sourcing
  flagged     multiple sensational indicators
  unverified  checked, but not enough indicators either way
"""

import psycopg2.extras

# A post is checked if ANY of its tags is in this set (case-insensitive).
NEWS_TAGS = {
    "news", "politics", "world", "economics", "health",
    "science", "government", "election", "crisis",
}

SENSATIONAL_KEYWORDS = [
    "breaking", "shocking", "you won't believe", "secret",
    "they don't want you to know", "miracle", "cure",
    "100% proven", "scientists baffled", "mainstream media won't",
]

CREDIBILITY_BOOSTERS = [
    "according to", "research shows", "study published",
    "data indicates", "peer reviewed", "official statement",
    "confirmed by", "reuters", "associated press",
]


def is_news(tags: list[str]) -> bool:
    """True if any tag is news-type, so the post must be fact-checked."""
    return any(tag.lower() in NEWS_TAGS for tag in tags)


class NewsChecker:
    """Analyzes post content for potential misinformation."""

    def check(self, content: str) -> dict:
        content_lower = content.lower()

        sensational_count = sum(
            1 for kw in SENSATIONAL_KEYWORDS if kw in content_lower
        )
        credibility_count = sum(
            1 for kw in CREDIBILITY_BOOSTERS if kw in content_lower
        )

        if sensational_count >= 3:
            return {
                "verdict": "flagged",
                "confidence": 0.3,
                "sources": [],
                "source_summary": "Content contains multiple sensational indicators. Recommend verification.",
            }
        elif sensational_count >= 1 and credibility_count == 0:
            return {
                "verdict": "mixed",
                "confidence": 0.5,
                "sources": [],
                "source_summary": "Content contains some sensational language. Consider checking sources.",
            }
        elif credibility_count >= 2:
            return {
                "verdict": "verified",
                "confidence": 0.8,
                "sources": [],
                "source_summary": "Content references credible sourcing patterns.",
            }
        else:
            return {
                "verdict": "unverified",
                "confidence": 0.5,
                "sources": [],
                "source_summary": "Insufficient indicators for automated verification.",
            }

    def save(self, cur, post_id: str, content: str, result: dict):
        """Record a verdict in news_verifications, on the caller's cursor."""
        cur.execute(
            """INSERT INTO news_verifications (post_id, claim_text, verdict, confidence, sources)
               VALUES (%s, %s, %s, %s, %s::jsonb)""",
            (
                post_id, content[:500], result["verdict"],
                result["confidence"],
                psycopg2.extras.Json(result["sources"]),
            ),
        )


news_checker = NewsChecker()
