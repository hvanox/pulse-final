"""
Feature extraction for ML level predictor.
Queries SQLite DB to build a feature vector for a given user.
"""

import json


TOPICS = ["stocks", "etf", "dividends", "risk", "diversification", "portfolio", "market_logic"]

FEATURE_COLUMNS = [
    "onboarding_score",
    "topic_stocks",
    "topic_etf",
    "topic_dividends",
    "topic_risk",
    "topic_diversification",
    "topic_portfolio",
    "topic_market_logic",
    "avg_time_ms",
    "correct_rate",
    "total_answers",
    "skip_count",
    "lessons_completed",
]


def extract_features(db, user_id: str) -> dict:
    """
    Extract ML features for a user from the database.

    Returns a dict with keys matching FEATURE_COLUMNS.
    Missing data defaults to 0.
    """
    features = {col: 0.0 for col in FEATURE_COLUMNS}

    # 1. Onboarding score + per-topic scores
    onb = db.execute(
        "SELECT score, topic_scores FROM onboarding_results WHERE user_id=?",
        (user_id,),
    ).fetchone()

    if onb:
        features["onboarding_score"] = float(onb["score"] or 0)
        if onb["topic_scores"]:
            try:
                topic_data = json.loads(onb["topic_scores"])
                for topic in TOPICS:
                    val = topic_data.get(topic, {})
                    if isinstance(val, dict):
                        features[f"topic_{topic}"] = float(val.get("score", 0))
                    else:
                        features[f"topic_{topic}"] = float(val or 0)
            except (json.JSONDecodeError, TypeError):
                pass

    # 2. Adaptive answer patterns
    answers = db.execute(
        "SELECT is_correct, time_ms FROM adaptive_answers WHERE user_id=?",
        (user_id,),
    ).fetchall()

    if answers:
        features["total_answers"] = float(len(answers))
        features["avg_time_ms"] = float(
            sum(a["time_ms"] for a in answers) / len(answers)
        )
        features["correct_rate"] = float(
            sum(1 for a in answers if a["is_correct"]) / len(answers)
        )

    # 3. Skip count (answers with time_ms == 0 treated as skips)
    skip_count = db.execute(
        "SELECT COUNT(*) as cnt FROM adaptive_answers WHERE user_id=? AND time_ms=0",
        (user_id,),
    ).fetchone()
    if skip_count:
        features["skip_count"] = float(skip_count["cnt"])

    # 4. Lessons completed
    lessons = db.execute(
        "SELECT COUNT(*) as cnt FROM lesson_completions WHERE user_id=?",
        (user_id,),
    ).fetchone()
    if lessons:
        features["lessons_completed"] = float(lessons["cnt"])

    return features
