import json
from datetime import datetime

TOPICS = [
    {"id": "stocks", "name": "Акции"},
    {"id": "etf", "name": "ETF и фонды"},
    {"id": "dividends", "name": "Дивиденды"},
    {"id": "risk", "name": "Риск"},
    {"id": "diversification", "name": "Диверсификация"},
    {"id": "portfolio", "name": "Портфель"},
    {"id": "market_logic", "name": "Логика рынка"},
]

TOPIC_MAP = {t["id"]: t for t in TOPICS}

ONBOARDING_LEVELS = [
    {
        "id": "novice",
        "name": "Новичок",
        "score_range": [0.0, 0.39],
        "start_module": "m1",
        "start_lesson": "1.1",
        "xp_bonus": 50,
    },
    {
        "id": "basic",
        "name": "Базовый",
        "score_range": [0.4, 0.69],
        "start_module": "m2",
        "start_lesson": "2.1",
        "xp_bonus": 150,
    },
    {
        "id": "advanced",
        "name": "Продвинутый",
        "score_range": [0.7, 1.0],
        "start_module": "m3",
        "start_lesson": "3.1",
        "xp_bonus": 300,
    },
]

SEED_ONBOARDING_QUESTIONS = [
    {
        "id": "ob_1",
        "topic": "stocks",
        "difficulty": 1,
        "type": "scenario",
        "scenario": "Друг купил акцию Apple.",
        "question": "Владеет ли он частью компании?",
        "options": [
            "Да, акция это доля",
            "Нет, это просто бумага",
            "Только если купил контрольный пакет",
            "Не знаю",
        ],
        "correct_index": 0,
        "weight": 1.0,
    },
    {
        "id": "ob_2",
        "topic": "market_logic",
        "difficulty": 1,
        "type": "scenario",
        "scenario": "Отчет компании хуже ожиданий рынка.",
        "question": "Что чаще происходит с ценой акции?",
        "options": ["Растет", "Падает", "Не меняется", "Не знаю"],
        "correct_index": 1,
        "weight": 1.0,
    },
    {
        "id": "ob_3",
        "topic": "risk",
        "difficulty": 2,
        "type": "decision",
        "scenario": "Весь капитал в одной акции и просадка 20%.",
        "question": "Главный вывод?",
        "options": [
            "Нужна диверсификация",
            "Акция плохая, надо другую",
            "Инвестирование это казино",
            "Надо торговать каждый час",
        ],
        "correct_index": 0,
        "weight": 1.2,
    },
    {
        "id": "ob_4",
        "topic": "dividends",
        "difficulty": 2,
        "type": "scenario",
        "scenario": "Инвестор получает деньги без продажи акций.",
        "question": "Что это?",
        "options": ["Дивиденды", "Кредит", "Ошибка банка", "Процент вклада"],
        "correct_index": 0,
        "weight": 1.0,
    },
    {
        "id": "ob_5",
        "topic": "diversification",
        "difficulty": 2,
        "type": "portfolio_choice",
        "scenario": "Нужно выбрать более защищенный портфель.",
        "question": "Какой вариант лучше диверсифицирован?",
        "options": [
            "100% в одну акцию",
            "Две акции одного сектора",
            "Пять компаний разных секторов",
            "Все одинаково",
        ],
        "correct_index": 2,
        "weight": 1.2,
    },
    {
        "id": "ob_6",
        "topic": "etf",
        "difficulty": 2,
        "type": "scenario",
        "scenario": "Нужно вложиться сразу в много компаний одной покупкой.",
        "question": "Какой инструмент подходит?",
        "options": ["ETF", "Вклад", "Облигация", "Кредит"],
        "correct_index": 0,
        "weight": 1.0,
    },
]


def load_onboarding_questions(db, include_answers: bool = False):
    rows = db.execute(
        """
        SELECT question_id, topic, difficulty, qtype, scenario, question, options_json, correct_index, weight
        FROM onboarding_questions
        WHERE is_active=1
        ORDER BY order_no, id
        """
    ).fetchall()
    questions = []
    for r in rows:
        options = json.loads(r["options_json"])
        q = {
            "id": r["question_id"],
            "topic": r["topic"],
            "difficulty": r["difficulty"],
            "type": r["qtype"],
            "scenario": r["scenario"],
            "question": r["question"],
            "options": options,
            "weight": float(r["weight"] or 1.0),
        }
        if include_answers:
            q["correct_index"] = int(r["correct_index"])
        questions.append(q)
    return questions


def validate_answers_payload(answers, questions):
    qmap = {q["id"]: q for q in questions}
    if not isinstance(answers, list) or not answers:
        return False, "answers must be a non-empty list"

    for a in answers:
        if not isinstance(a, dict):
            return False, "each answer must be an object"
        qid = a.get("question_id")
        selected_index = a.get("selected_index")
        if qid not in qmap:
            return False, f"unknown question_id: {qid}"
        if not isinstance(selected_index, int):
            return False, f"selected_index must be int for question {qid}"
        if selected_index < 0 or selected_index >= len(qmap[qid]["options"]):
            return False, f"selected_index out of range for question {qid}"
    return True, None


def score_onboarding(answers, questions):
    qmap = {q["id"]: q for q in questions}
    topic_stats = {}
    details = []
    total_score = 0.0
    max_score = 0.0

    for ans in answers:
        q = qmap.get(ans["question_id"])
        if not q:
            continue
        topic = q["topic"]
        topic_stats.setdefault(topic, {"correct": 0, "total": 0})

        chosen = ans["selected_index"]
        is_correct = chosen == q["correct_index"]
        weight = float(q.get("weight", 1.0))
        difficulty_mult = 1 + (float(q.get("difficulty", 1)) * 0.5)
        question_max = weight * difficulty_mult
        score = question_max if is_correct else 0.0

        total_score += score
        max_score += question_max
        topic_stats[topic]["total"] += 1
        topic_stats[topic]["correct"] += int(is_correct)

        details.append(
            {
                "question_id": q["id"],
                "topic": topic,
                "is_correct": is_correct,
                "time_ms": int(ans.get("time_ms", 0) or 0),
            }
        )

    normalized = round(total_score / max_score, 4) if max_score > 0 else 0.0
    level = ONBOARDING_LEVELS[0]
    for lvl in ONBOARDING_LEVELS:
        low, high = lvl["score_range"]
        if low <= normalized <= high:
            level = lvl
            break

    topic_scores = {}
    for topic_id, stats in topic_stats.items():
        total = stats["total"]
        score = round(stats["correct"] / total, 2) if total else 0.0
        topic_scores[topic_id] = {
            **TOPIC_MAP.get(topic_id, {"id": topic_id, "name": topic_id}),
            "correct": stats["correct"],
            "total": total,
            "score": score,
            "mastery": score,
        }

    sorted_topics = sorted(topic_scores.values(), key=lambda x: x["score"], reverse=True)
    strong_topics = [x for x in sorted_topics if x["score"] >= 0.7][:3]
    weak_topics = [x for x in sorted_topics if x["score"] < 0.5][:3]

    return {
        "level": level,
        "score": round(normalized, 2),
        "score_pct": round(normalized * 100),
        "topic_scores": topic_scores,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "recommended_start": {"module": level["start_module"], "lesson": level["start_lesson"]},
        "xp_bonus": level["xp_bonus"],
        "details": details,
        "total_correct": sum(1 for d in details if d["is_correct"]),
        "total_questions": len(details),
    }


def compute_topic_mastery(db, user_id: str):
    mastery = {t["id"]: {"mastery": 0.0, "answers": 0, "correct": 0, **t} for t in TOPICS}

    rows = db.execute(
        "SELECT topic, is_correct FROM adaptive_answers WHERE user_id=? ORDER BY created_at DESC LIMIT 200",
        (user_id,),
    ).fetchall()
    for row in rows:
        topic = row["topic"]
        if topic not in mastery:
            continue
        mastery[topic]["answers"] += 1
        mastery[topic]["correct"] += int(row["is_correct"])

    for topic_id, data in mastery.items():
        if data["answers"] > 0:
            data["mastery"] = round(data["correct"] / data["answers"], 2)
    return mastery


def get_weak_topics(mastery: dict, threshold: float = 0.5):
    weak = [m for m in mastery.values() if m["mastery"] < threshold or m["answers"] < 3]
    weak.sort(key=lambda x: x["mastery"])
    return weak


def get_strong_topics(mastery: dict, threshold: float = 0.7):
    strong = [m for m in mastery.values() if m["mastery"] >= threshold and m["answers"] >= 3]
    strong.sort(key=lambda x: x["mastery"], reverse=True)
    return strong


def recommend_next_content(db, user_id: str, mastery: dict):
    weak = get_weak_topics(mastery)
    if weak:
        return {
            "type": "lesson",
            "topic_focus": weak[0]["id"],
            "reason": f"Сфокусироваться на теме: {weak[0]['name']}",
        }
    return {"type": "lesson", "topic_focus": None, "reason": "Продолжай текущий модуль"}


def get_topics_due_for_review(db, user_id: str, mastery: dict):
    now = datetime.utcnow()
    due = []
    rows = db.execute(
        "SELECT topic, MAX(created_at) AS last_at FROM adaptive_answers WHERE user_id=? GROUP BY topic",
        (user_id,),
    ).fetchall()
    for row in rows:
        topic = row["topic"]
        if topic not in mastery or not row["last_at"]:
            continue
        try:
            last_at = datetime.fromisoformat(row["last_at"])
        except ValueError:
            continue
        days = (now - last_at).days
        if days >= 7 and mastery[topic]["mastery"] < 0.8:
            due.append({**mastery[topic], "days_since_review": days})
    due.sort(key=lambda x: x["mastery"])
    return due
