"""
News Checker
-------------
Fake news detection for Realm posts.
MVP: heuristic-based keyword analysis.
Production: integrate with Google Fact Check API, NewsAPI, ClaimBuster, etc.
"""

from .database import query_returning, execute

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
                "verdict": "pending",
                "confidence": 0.5,
                "sources": [],
                "source_summary": "Insufficient indicators for automated verification.",
            }

    def check_and_store(self, post_id: str, content: str):
        """Check content and save result to the database."""
        result = self.check(content)

        import psycopg2.extras
        from .database import get_db

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO news_verifications (post_id, claim_text, verdict, confidence, sources)
                   VALUES (%s, %s, %s, %s, %s::jsonb)""",
                (
                    post_id, content[:500], result["verdict"],
                    result["confidence"],
                    psycopg2.extras.Json(result["sources"]),
                ),
            )
            cur.execute(
                "UPDATE posts SET verification_status = %s, verification_source = %s WHERE id = %s",
                (result["verdict"], result.get("source_summary", ""), post_id),
            )
            cur.close()

        return result


news_checker = NewsChecker()
