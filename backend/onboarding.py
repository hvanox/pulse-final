"""
Pulse 2.0 — Onboarding Test & Adaptive Learning Engine

Onboarding test design:
- 10 questions, ~3-4 minutes
- Not a boring exam — presented as an "Investment Quest"
- Covers 7 topic areas with adaptive difficulty
- Each question is a scenario/situation, not a textbook quiz
- Determines: level (novice/basic/advanced), strong topics, weak topics
- Generates personalized learning plan

Adaptive learning engine:
- Tracks per-topic mastery scores (0.0 to 1.0)
- Uses spaced repetition with decay
- Prioritizes weak topics in lesson recommendations
- Adjusts difficulty based on performance patterns
"""

import json
import math
from datetime import datetime, timedelta

# ═══════════════════════════════════════════
# TOPIC TAXONOMY
# ═══════════════════════════════════════════

TOPICS = [
    {"id": "stocks", "name": "Акции", "icon": "📈", "color": "#4caf50"},
    {"id": "etf", "name": "ETF и фонды", "icon": "📦", "color": "#2196f3"},
    {"id": "dividends", "name": "Дивиденды", "icon": "💰", "color": "#ff9800"},
    {"id": "risk", "name": "Риск", "icon": "⚠️", "color": "#f44336"},
    {"id": "diversification", "name": "Диверсификация", "icon": "🎨", "color": "#9c27b0"},
    {"id": "portfolio", "name": "Портфель", "icon": "💼", "color": "#607d8b"},
    {"id": "market_logic", "name": "Логика рынка", "icon": "🧠", "color": "#00bcd4"},
]

TOPIC_MAP = {t["id"]: t for t in TOPICS}

# ═══════════════════════════════════════════
# ONBOARDING TEST — 10 SCENARIO-BASED QUESTIONS
# ═══════════════════════════════════════════
# Design principles:
# - Each question is a SCENARIO, not a definition quiz
# - User makes DECISIONS in real-world-like situations
# - Mix of formats: scenarios, chart reading, sorting
# - Adaptive: if Q1 (easy) correct → skip to Q3 (medium)
# - Time: ~20 seconds per question = 3-4 min total

ONBOARDING_QUESTIONS = [
    # ─── Q1: STOCKS — Easy (scenario) ───
    {
        "id": "ob_1",
        "topic": "stocks",
        "difficulty": 1,
        "type": "scenario",
        "scenario": "Твой друг говорит: «Я купил акцию Apple — теперь я владею кусочком компании!»",
        "question": "Прав ли он?",
        "options": [
            {"text": "Да! Акция — это доля в компании", "is_correct": True},
            {"text": "Нет, акция — это просто бумажка", "is_correct": False},
            {"text": "Только если он купил больше 50% акций", "is_correct": False},
            {"text": "Не знаю, что такое акция", "is_correct": False, "is_skip": True},
        ],
        "explanation": "Акция — это доля в компании. Владелец даже 1 акции Apple — совладелец бизнеса.",
        "weight": 1.0,
    },
    # ─── Q2: MARKET LOGIC — Easy (news reaction) ───
    {
        "id": "ob_2",
        "topic": "market_logic",
        "difficulty": 1,
        "type": "news_reaction",
        "scenario": "Новость: «Tesla отчиталась хуже ожиданий аналитиков»",
        "question": "Что скорее всего произойдёт с акцией Tesla?",
        "options": [
            {"text": "Акция вырастет — компания же прибыльная", "is_correct": False},
            {"text": "Акция упадёт — результат хуже ожиданий", "is_correct": True},
            {"text": "Ничего не изменится", "is_correct": False},
            {"text": "Затрудняюсь ответить", "is_correct": False, "is_skip": True},
        ],
        "explanation": "Рынок торгует ожидания. Если результат хуже ожиданий — акция обычно падает, даже если компания прибыльна.",
        "weight": 1.0,
    },
    # ─── Q3: RISK — Medium (portfolio decision) ───
    {
        "id": "ob_3",
        "topic": "risk",
        "difficulty": 2,
        "type": "decision",
        "scenario": "У тебя 500 000 ₽. Ты вложил ВСЁ в одну акцию — Nvidia. За неделю она упала на 20%.",
        "question": "Какой главный урок из этой ситуации?",
        "options": [
            {"text": "Nvidia — плохая компания, надо было выбрать другую", "is_correct": False},
            {"text": "Нельзя вкладывать всё в одну акцию — нужна диверсификация", "is_correct": True},
            {"text": "Надо было продать раньше — нужно следить за рынком каждый час", "is_correct": False},
            {"text": "Инвестирование — это просто казино", "is_correct": False},
        ],
        "explanation": "Главная ошибка — концентрация в одной акции. Диверсификация защищает от таких просадок.",
        "weight": 1.2,
    },
    # ─── Q4: DIVIDENDS — Medium (passive income) ───
    {
        "id": "ob_4",
        "topic": "dividends",
        "difficulty": 2,
        "type": "scenario",
        "scenario": "Маша купила акции Сбербанка и каждый год получает деньги на счёт, хотя ничего не продаёт.",
        "question": "Откуда берутся эти деньги?",
        "options": [
            {"text": "Это проценты по вкладу", "is_correct": False},
            {"text": "Это дивиденды — часть прибыли компании", "is_correct": True},
            {"text": "Это ошибка банка", "is_correct": False},
            {"text": "Не знаю", "is_correct": False, "is_skip": True},
        ],
        "explanation": "Дивиденды — это часть прибыли, которую компания распределяет между акционерами.",
        "weight": 1.0,
    },
    # ─── Q5: DIVERSIFICATION — Medium (portfolio builder) ───
    {
        "id": "ob_5",
        "topic": "diversification",
        "difficulty": 2,
        "type": "portfolio_choice",
        "scenario": "Тебе нужно выбрать портфель. Какой из них лучше защищён от рисков?",
        "question": "Выбери наиболее диверсифицированный портфель:",
        "options": [
            {"text": "100% в Tesla", "is_correct": False},
            {"text": "50% Apple + 50% Microsoft", "is_correct": False},
            {"text": "Apple + Сбербанк + Coca-Cola + Газпром + Nvidia (по 20%)", "is_correct": True},
            {"text": "Все варианты одинаковы", "is_correct": False},
        ],
        "explanation": "Третий портфель — 5 компаний из разных секторов и стран. Это настоящая диверсификация!",
        "weight": 1.2,
    },
    # ─── Q6: ETF — Medium (concept) ───
    {
        "id": "ob_6",
        "topic": "etf",
        "difficulty": 2,
        "type": "scenario",
        "scenario": "Коля хочет вложить в 500 компаний, но у него нет времени выбирать каждую.",
        "question": "Какой инструмент позволит ему это сделать одной покупкой?",
        "options": [
            {"text": "Банковский вклад", "is_correct": False},
            {"text": "ETF (биржевой фонд)", "is_correct": True},
            {"text": "Облигация", "is_correct": False},
            {"text": "Не знаю, что такое ETF", "is_correct": False, "is_skip": True},
        ],
        "explanation": "ETF — это фонд, который содержит сотни акций. Одна покупка = мгновенная диверсификация.",
        "weight": 1.0,
    },
    # ─── Q7: PORTFOLIO — Hard (P/E understanding) ───
    {
        "id": "ob_7",
        "topic": "portfolio",
        "difficulty": 3,
        "type": "analysis",
        "scenario": "Две компании:\n• Сбербанк: P/E = 4.5, дивиденды 9.5%\n• Nvidia: P/E = 70, дивиденды 0.03%",
        "question": "Что означает низкий P/E Сбербанка по сравнению с Nvidia?",
        "options": [
            {"text": "Сбербанк дороже Nvidia", "is_correct": False},
            {"text": "Акция Сбербанка дешевле относительно прибыли — окупается быстрее", "is_correct": True},
            {"text": "P/E не имеет значения", "is_correct": False},
            {"text": "Не знаю, что такое P/E", "is_correct": False, "is_skip": True},
        ],
        "explanation": "P/E = Цена / Прибыль. P/E 4.5 значит окупаемость 4.5 года. P/E 70 — инвесторы платят за будущий рост.",
        "weight": 1.5,
    },
    # ─── Q8: MARKET LOGIC — Hard (crisis behavior) ───
    {
        "id": "ob_8",
        "topic": "market_logic",
        "difficulty": 3,
        "type": "crisis",
        "scenario": "Март 2020, COVID. Твой портфель упал на 35% за месяц. Все вокруг в панике.",
        "question": "Какое решение с точки зрения истории было бы лучшим?",
        "options": [
            {"text": "Продать всё, пока не упало ещё больше", "is_correct": False},
            {"text": "Ничего не делать или докупить — рынок исторически всегда восстанавливался", "is_correct": True},
            {"text": "Переложить всё в криптовалюту", "is_correct": False},
            {"text": "Закрыть приложение и забыть", "is_correct": False},
        ],
        "explanation": "После COVID-обвала рынок восстановился за 5 месяцев. Те, кто покупал на дне, заработали +80%.",
        "weight": 1.5,
    },
    # ─── Q9: STOCKS — Hard (compound interest) ───
    {
        "id": "ob_9",
        "topic": "stocks",
        "difficulty": 3,
        "type": "calculation",
        "scenario": "Аня вкладывает 10 000 ₽/мес под 10% годовых. Борис начал на 10 лет позже, но вкладывает 20 000 ₽/мес.",
        "question": "Кто накопит больше к пенсии?",
        "options": [
            {"text": "Борис — он вкладывает больше денег", "is_correct": False},
            {"text": "Аня — сложный процент и время важнее суммы", "is_correct": True},
            {"text": "Результат будет одинаковым", "is_correct": False},
            {"text": "Невозможно сказать без калькулятора", "is_correct": False},
        ],
        "explanation": "Сложный процент делает чудеса. 10 дополнительных лет > двойной взнос. Время — главный актив инвестора.",
        "weight": 1.5,
    },
    # ─── Q10: RISK — Hard (emotional intelligence) ───
    {
        "id": "ob_10",
        "topic": "risk",
        "difficulty": 3,
        "type": "emotional",
        "scenario": "Все твои друзья купили акции «хайповой» компании. Она выросла на 300% за месяц. P/E = 500.",
        "question": "Что бы ты сделал?",
        "options": [
            {"text": "Куплю тоже — не хочу упустить!", "is_correct": False},
            {"text": "Это опасно — P/E 500 говорит о пузыре. Лучше подождать", "is_correct": True},
            {"text": "Вложу половину — компромисс", "is_correct": False},
            {"text": "Продам всё остальное и куплю только эту акцию", "is_correct": False},
        ],
        "explanation": "FOMO (страх упустить) — самая дорогая эмоция. P/E 500 — это пузырь. Баффет: «Будь осторожен, когда другие жадничают».",
        "weight": 1.5,
    },
]

QUESTION_MAP = {q["id"]: q for q in ONBOARDING_QUESTIONS}

# ═══════════════════════════════════════════
# ONBOARDING LEVELS
# ═══════════════════════════════════════════

ONBOARDING_LEVELS = [
    {
        "id": "novice",
        "name": "Новичок",
        "name_full": "Начинающий инвестор",
        "icon": "🌱",
        "color": "#4caf50",
        "description": "Ты только начинаешь свой путь в мире инвестиций. Это отлично — мы начнём с самых основ!",
        "score_range": [0, 0.39],
        "start_module": "m1",
        "start_lesson": "1.1",
        "xp_bonus": 50,
    },
    {
        "id": "basic",
        "name": "Базовый",
        "name_full": "Осведомлённый новичок",
        "icon": "📊",
        "color": "#2196f3",
        "description": "Ты знаешь основы! Можно пропустить введение и перейти к практике с акциями.",
        "score_range": [0.4, 0.69],
        "start_module": "m2",
        "start_lesson": "2.1",
        "xp_bonus": 150,
    },
    {
        "id": "advanced",
        "name": "Продвинутый",
        "name_full": "Продвинутый новичок",
        "icon": "🚀",
        "color": "#ff9800",
        "description": "Впечатляет! У тебя хорошая база. Мы сфокусируемся на стратегиях и продвинутых инструментах.",
        "score_range": [0.7, 1.0],
        "start_module": "m3",
        "start_lesson": "3.1",
        "xp_bonus": 300,
    },
]


# ═══════════════════════════════════════════
# SCORING & LEVEL DETERMINATION
# ═══════════════════════════════════════════

def score_onboarding(answers: list) -> dict:
    """
    Score onboarding test answers and determine user level.

    answers: list of {"question_id": str, "selected_index": int, "time_ms": int}

    Returns: {
        level, score, topic_scores, strong_topics, weak_topics,
        recommended_start, xp_bonus, details
    }
    """
    topic_correct = {}  # topic -> [correct_count, total_count, weighted_score]
    total_weighted_score = 0
    max_weighted_score = 0
    details = []

    for ans in answers:
        q = QUESTION_MAP.get(ans.get("question_id"))
        if not q:
            continue

        topic = q["topic"]
        if topic not in topic_correct:
            topic_correct[topic] = [0, 0, 0.0]

        selected = ans.get("selected_index", -1)
        is_correct = False
        is_skip = False

        if 0 <= selected < len(q["options"]):
            opt = q["options"][selected]
            is_correct = opt.get("is_correct", False)
            is_skip = opt.get("is_skip", False)

        weight = q["weight"]
        difficulty_mult = q["difficulty"] * 0.5  # higher difficulty = more weight

        if is_correct:
            score = weight * (1 + difficulty_mult)
            topic_correct[topic][0] += 1
        elif is_skip:
            score = 0  # "don't know" = 0 but not negative
        else:
            score = -weight * 0.3  # wrong answer slightly negative

        topic_correct[topic][1] += 1
        topic_correct[topic][2] += max(0, score)
        total_weighted_score += max(0, score)
        max_weighted_score += weight * (1 + difficulty_mult)

        # Time bonus: faster correct answers = higher confidence
        time_ms = ans.get("time_ms", 15000)
        time_bonus = 0
        if is_correct and time_ms < 8000:
            time_bonus = 0.1  # quick confident answer
        total_weighted_score += time_bonus

        details.append({
            "question_id": q["id"],
            "topic": topic,
            "difficulty": q["difficulty"],
            "is_correct": is_correct,
            "is_skip": is_skip,
            "score": round(score, 2),
            "time_ms": time_ms,
        })

    # Normalize score to 0-1
    overall_score = total_weighted_score / max_weighted_score if max_weighted_score > 0 else 0
    overall_score = max(0, min(1, overall_score))

    # Per-topic scores (0-1)
    topic_scores = {}
    for topic_id, (correct, total, weighted) in topic_correct.items():
        topic_scores[topic_id] = {
            "correct": correct,
            "total": total,
            "score": round(correct / total, 2) if total > 0 else 0,
            "mastery": round(weighted / (total * 2) if total > 0 else 0, 2),  # normalized
            **TOPIC_MAP.get(topic_id, {}),
        }

    # Determine strong/weak topics
    sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1]["score"], reverse=True)
    strong_topics = [t for t_id, t in sorted_topics if t["score"] >= 0.7]
    weak_topics = [t for t_id, t in sorted_topics if t["score"] < 0.5]

    # Fill in missing topics as weak
    tested_topics = set(topic_scores.keys())
    for topic in TOPICS:
        if topic["id"] not in tested_topics:
            weak_topics.append({**topic, "correct": 0, "total": 0, "score": 0, "mastery": 0})

    # Determine level
    level = ONBOARDING_LEVELS[0]  # default: novice
    for lvl in ONBOARDING_LEVELS:
        low, high = lvl["score_range"]
        if low <= overall_score <= high:
            level = lvl
            break
    # If score > last range, use last level
    if overall_score > ONBOARDING_LEVELS[-1]["score_range"][1]:
        level = ONBOARDING_LEVELS[-1]

    # Generate learning plan
    plan = generate_learning_plan(level, topic_scores, strong_topics, weak_topics)

    return {
        "level": level,
        "score": round(overall_score, 2),
        "score_pct": round(overall_score * 100),
        "topic_scores": topic_scores,
        "strong_topics": strong_topics[:3],
        "weak_topics": weak_topics[:3],
        "recommended_start": {"module": level["start_module"], "lesson": level["start_lesson"]},
        "xp_bonus": level["xp_bonus"],
        "learning_plan": plan,
        "details": details,
        "total_correct": sum(1 for d in details if d["is_correct"]),
        "total_questions": len(details),
    }


def generate_learning_plan(level, topic_scores, strong_topics, weak_topics):
    """Generate personalized learning plan based on test results."""
    plan = []

    if level["id"] == "novice":
        plan = [
            {"priority": "high", "action": "Начни с основ инвестирования", "module": "m1", "reason": "Фундамент для всего"},
            {"priority": "high", "action": "Изучи что такое акции", "module": "m2", "reason": "Базовый инструмент"},
            {"priority": "medium", "action": "Пойми риски и диверсификацию", "module": "m3", "reason": "Защита капитала"},
        ]
    elif level["id"] == "basic":
        plan = [
            {"priority": "high", "action": "Перейди к практике с акциями", "module": "m2", "reason": "У тебя есть база — пора действовать"},
            {"priority": "high", "action": "Освой управление рисками", "module": "m3", "reason": "Ключевой навык"},
            {"priority": "medium", "action": "Изучи инструменты анализа", "module": "m4", "reason": "P/E, графики, ETF"},
        ]
    else:  # advanced
        plan = [
            {"priority": "high", "action": "Изучи продвинутые стратегии", "module": "m5", "reason": "DCA, дивидендная стратегия"},
            {"priority": "medium", "action": "Практика на реальных кейсах", "module": "m6", "reason": "Кризис 2008, Tesla bubble"},
            {"priority": "medium", "action": "Углуби знания в ETF", "module": "m4", "reason": "Продвинутые инструменты"},
        ]

    # Add weak topic recommendations
    for wt in weak_topics[:2]:
        topic_to_module = {
            "stocks": "m2", "etf": "m4", "dividends": "m4",
            "risk": "m3", "diversification": "m3",
            "portfolio": "m2", "market_logic": "m2",
        }
        mod = topic_to_module.get(wt.get("id", ""), "m1")
        plan.append({
            "priority": "focus",
            "action": f"Подтяни тему: {wt.get('name', '')}",
            "module": mod,
            "reason": f"Тест показал пробел в этой области",
        })

    return plan


# ═══════════════════════════════════════════
# ADAPTIVE LEARNING ENGINE
# ═══════════════════════════════════════════

# Default mastery for each topic
DEFAULT_MASTERY = {t["id"]: 0.0 for t in TOPICS}


def compute_topic_mastery(db, user_id: str) -> dict:
    """
    Compute per-topic mastery scores from all user interactions.
    Uses exponential decay: recent answers matter more.

    Returns: {topic_id: {"mastery": 0.0-1.0, "answers": int, "recent_trend": str}}
    """
    # Get all onboarding + lesson quiz answers
    mastery = {t["id"]: {"correct": 0, "total": 0, "weighted": 0.0, "recent": []} for t in TOPICS}

    # From onboarding results
    onb = db.execute(
        "SELECT topic_scores FROM onboarding_results WHERE user_id=? ORDER BY completed_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if onb and onb["topic_scores"]:
        try:
            scores = json.loads(onb["topic_scores"])
            for topic_id, data in scores.items():
                if topic_id in mastery:
                    mastery[topic_id]["correct"] += data.get("correct", 0)
                    mastery[topic_id]["total"] += data.get("total", 0)
                    mastery[topic_id]["weighted"] += data.get("mastery", 0) * 0.5  # onboarding = half weight
        except (json.JSONDecodeError, TypeError):
            pass

    # From adaptive tracking table
    rows = db.execute(
        "SELECT topic, is_correct, created_at FROM adaptive_answers WHERE user_id=? ORDER BY created_at DESC LIMIT 200",
        (user_id,),
    ).fetchall()

    now = datetime.utcnow()
    for r in rows:
        topic = r["topic"]
        if topic not in mastery:
            continue
        is_correct = bool(r["is_correct"])
        # Exponential decay: recent answers matter more
        try:
            created = datetime.fromisoformat(r["created_at"])
            days_ago = (now - created).days
        except (ValueError, TypeError):
            days_ago = 0
        decay = math.exp(-0.05 * days_ago)  # half-life ~14 days

        mastery[topic]["total"] += 1
        if is_correct:
            mastery[topic]["correct"] += 1
            mastery[topic]["weighted"] += decay * 1.0
        else:
            mastery[topic]["weighted"] -= decay * 0.3
        mastery[topic]["recent"].append(is_correct)

    # Normalize to 0-1
    result = {}
    for topic_id, data in mastery.items():
        if data["total"] == 0:
            score = 0.0
        else:
            raw = data["correct"] / data["total"]
            # Blend with weighted (recency-adjusted)
            weighted_norm = max(0, min(1, data["weighted"] / max(data["total"] * 0.5, 1)))
            score = raw * 0.4 + weighted_norm * 0.6

        # Recent trend
        recent = data["recent"][:5]
        if len(recent) >= 3:
            recent_rate = sum(recent) / len(recent)
            if recent_rate >= 0.8:
                trend = "improving"
            elif recent_rate <= 0.3:
                trend = "struggling"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        result[topic_id] = {
            "mastery": round(max(0, min(1, score)), 2),
            "answers": data["total"],
            "correct": data["correct"],
            "recent_trend": trend,
            **TOPIC_MAP.get(topic_id, {}),
        }

    return result


def get_weak_topics(mastery: dict, threshold: float = 0.5) -> list:
    """Get topics where user needs more practice."""
    weak = []
    for topic_id, data in mastery.items():
        if data["mastery"] < threshold or data["answers"] < 3:
            weak.append(data)
    weak.sort(key=lambda x: x["mastery"])
    return weak


def get_strong_topics(mastery: dict, threshold: float = 0.7) -> list:
    """Get topics where user is doing well."""
    strong = [data for data in mastery.values() if data["mastery"] >= threshold and data["answers"] >= 3]
    strong.sort(key=lambda x: x["mastery"], reverse=True)
    return strong


def recommend_next_content(db, user_id: str, mastery: dict) -> dict:
    """
    Recommend next lesson/topic based on adaptive analysis.

    Algorithm:
    1. Find weakest topic with mastery < 0.5
    2. If weak topic found → recommend lesson from that topic's module
    3. If struggling (recent_trend) → insert review exercise
    4. If all topics > 0.7 → advance to next module
    5. Apply spaced repetition: re-surface old weak topics periodically
    """
    weak = get_weak_topics(mastery)
    struggling = [t for t in mastery.values() if t["recent_trend"] == "struggling"]

    # Check what user has completed
    completions = db.execute(
        "SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user_id,)
    ).fetchall()
    completed_ids = {r["lesson_id"] for r in completions}

    # Topic to relevant lessons mapping
    topic_lessons = {
        "stocks": ["2.1", "2.2", "2.3", "2.4", "2.5"],
        "etf": ["4.2"],
        "dividends": ["4.4", "5.3"],
        "risk": ["3.1", "3.3", "3.4"],
        "diversification": ["3.2"],
        "portfolio": ["1.4", "2.5", "5.4"],
        "market_logic": ["2.3", "4.1", "4.3"],
    }

    recommendation = {
        "type": "lesson",
        "reason": "",
        "topic_focus": None,
        "lesson_id": None,
        "review_needed": False,
    }

    # Priority 1: Struggling topic — needs review
    if struggling:
        topic = struggling[0]
        recommendation["type"] = "review"
        recommendation["reason"] = f"Ты испытываешь трудности с темой «{topic.get('name', '')}». Давай повторим!"
        recommendation["topic_focus"] = topic.get("id")
        recommendation["review_needed"] = True
        # Find uncompleted lesson in this topic
        for lid in topic_lessons.get(topic.get("id", ""), []):
            if lid not in completed_ids:
                recommendation["lesson_id"] = lid
                break

    # Priority 2: Weak topic — needs learning
    elif weak:
        topic = weak[0]
        recommendation["reason"] = f"Тема «{topic.get('name', '')}» нуждается в прокачке"
        recommendation["topic_focus"] = topic.get("id")
        for lid in topic_lessons.get(topic.get("id", ""), []):
            if lid not in completed_ids:
                recommendation["lesson_id"] = lid
                break

    # Priority 3: Spaced repetition — re-surface old topics
    else:
        # Find topic that hasn't been practiced recently
        oldest_topic = None
        for topic_id, data in mastery.items():
            if data["answers"] > 0 and data["mastery"] < 0.9:
                if oldest_topic is None or data["answers"] < mastery[oldest_topic]["answers"]:
                    oldest_topic = topic_id
        if oldest_topic:
            recommendation["type"] = "reinforce"
            recommendation["reason"] = f"Давай закрепим тему «{mastery[oldest_topic].get('name', '')}»"
            recommendation["topic_focus"] = oldest_topic

    return recommendation


# ═══════════════════════════════════════════
# SPACED REPETITION SCHEDULER
# ═══════════════════════════════════════════

def get_review_interval(mastery_score: float, consecutive_correct: int) -> int:
    """
    Calculate days until next review based on mastery and streak.
    Inspired by SM-2 algorithm but simplified.

    mastery < 0.3: review in 1 day
    mastery 0.3-0.5: review in 2-3 days
    mastery 0.5-0.7: review in 5-7 days
    mastery > 0.7: review in 14+ days
    """
    if mastery_score < 0.3:
        base = 1
    elif mastery_score < 0.5:
        base = 2
    elif mastery_score < 0.7:
        base = 5
    else:
        base = 14

    # Consecutive correct answers extend interval
    multiplier = 1 + (consecutive_correct * 0.5)
    return int(base * multiplier)


def get_topics_due_for_review(db, user_id: str, mastery: dict) -> list:
    """Get topics that are due for spaced repetition review."""
    due = []
    now = datetime.utcnow()

    for topic_id, data in mastery.items():
        if data["answers"] == 0:
            continue

        # Get last answer date for this topic
        last = db.execute(
            "SELECT created_at FROM adaptive_answers WHERE user_id=? AND topic=? ORDER BY created_at DESC LIMIT 1",
            (user_id, topic_id),
        ).fetchone()

        if last:
            try:
                last_date = datetime.fromisoformat(last["created_at"])
                days_since = (now - last_date).days
                interval = get_review_interval(data["mastery"], data.get("correct", 0))
                if days_since >= interval:
                    due.append({
                        **data,
                        "days_since_review": days_since,
                        "interval": interval,
                    })
            except (ValueError, TypeError):
                pass

    due.sort(key=lambda x: x["mastery"])
    return due
