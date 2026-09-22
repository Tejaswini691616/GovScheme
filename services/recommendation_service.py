# PATH: GovScheme/services/recommendation_service.py
# Compatibility facade: the single recommendation implementation lives in ai.recommendation_model.
from ai.recommendation_model import get_recommendations, get_eligible_schemes_with_explanations, get_all_eligibility_results
from models.db import execute


def refresh_user_recommendations(user_row, top_k=5):
    """Refresh persisted rankings without retraining the model."""
    recommendations = get_recommendations(user_row, top_k=top_k)
    for rank, rec in enumerate(recommendations, 1):
        execute(
            """INSERT INTO recommendations(user_id,scheme_id,relevance_score,rank,generated_at)
               VALUES(?,?,?,?,datetime('now'))
               ON CONFLICT(user_id,scheme_id) DO UPDATE SET relevance_score=excluded.relevance_score,
                 rank=excluded.rank,generated_at=datetime('now')""",
            (user_row["user_id"], rec["scheme"]["scheme_id"], rec["relevance_score"], rank),
        )
    # Remove stale persisted recommendations that are no longer in the current
    # eligible top-K set. This prevents outdated scheme changes from remaining
    # visible in historical/current recommendation surfaces.
    ids = [rec["scheme"]["scheme_id"] for rec in recommendations]
    if ids:
        placeholders = ",".join("?" for _ in ids)
        execute(f"DELETE FROM recommendations WHERE user_id=? AND scheme_id NOT IN ({placeholders})", (user_row["user_id"], *ids))
    else:
        execute("DELETE FROM recommendations WHERE user_id=?", (user_row["user_id"],))
    return recommendations


__all__=["get_recommendations","get_eligible_schemes_with_explanations","get_all_eligibility_results","refresh_user_recommendations"]
