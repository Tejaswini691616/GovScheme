# PATH: GovScheme/models/feedback_model.py
from models.db import query, query_one, execute

VALID_FEATURES = ["Chatbot", "Recommendations", "Applications", "Help", "Voice Assistant", "Website"]


def create_feedback(user_id, rating: int, comment: str, language: str = "English",
                     voice_transcribed: bool = False, feature: str = None, page: str = None):
    return execute("""
        INSERT INTO feedback (user_id, rating, comment, language, voice_transcribed, feature, page)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, rating, comment, language, 1 if voice_transcribed else 0, feature, page))


def get_feedback_summary():
    """Returns overall average/count and the 1-5 star breakdown, for the
    admin feedback analytics view (master prompt: "ADMIN FEEDBACK
    ANALYTICS")."""
    overall = query_one("SELECT AVG(rating) as avg_rating, COUNT(*) as total FROM feedback")
    star_counts = {i: 0 for i in range(1, 6)}
    for row in query("SELECT rating, COUNT(*) as c FROM feedback GROUP BY rating"):
        star_counts[row["rating"]] = row["c"]

    feature_ratings = query("""
        SELECT feature, AVG(rating) as avg_rating, COUNT(*) as total
        FROM feedback WHERE feature IS NOT NULL
        GROUP BY feature
    """)

    return {
        "average_rating": round(overall["avg_rating"], 2) if overall and overall["avg_rating"] else None,
        "total_feedback": overall["total"] if overall else 0,
        "star_counts": star_counts,
        "feature_ratings": feature_ratings,
    }


def get_recent_feedback(limit=20):
    return query("""
        SELECT f.*, u.full_name FROM feedback f LEFT JOIN users u ON f.user_id = u.user_id
        ORDER BY f.created_at DESC LIMIT ?
    """, (limit,))
