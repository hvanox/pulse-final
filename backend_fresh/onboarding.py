import json
from datetime import datetime

TOPICS = [
    {"id": "stocks", "name": "Акции", "icon": "📈"},
    {"id": "etf", "name": "ETF и фонды", "icon": "🏦"},
    {"id": "dividends", "name": "Дивиденды", "icon": "💰"},
    {"id": "risk", "name": "Риск", "icon": "⚠️"},
    {"id": "diversification", "name": "Диверсификация", "icon": "🎯"},
    {"id": "portfolio", "name": "Портфель", "icon": "💼"},
    {"id": "market_logic", "name": "Логика рынка", "icon": "🧠"},
]

TOPIC_MAP = {t["id"]: t for t in TOPICS}

ONBOARDING_LEVELS = [
    {
        "id": "novice",
        "name": "Новичок",
        "name_full": "Начинающий инвестор",
        "icon": "🌱",
        "color": "#4caf50",
        "description": "Ты только начинаешь путь в мир инвестиций. Мы проведём тебя от основ к первым сделкам!",
        "score_range": [0.0, 0.39],
        "start_module": "m1",
        "start_lesson": "1.1",
        "xp_bonus": 50,
    },
    {
        "id": "basic",
        "name": "Базовый",
        "name_full": "Осознанный инвестор",
        "icon": "📊",
        "color": "#FFD600",
        "description": "У тебя есть базовое понимание рынка. Время углубить знания и начать практику!",
        "score_range": [0.4, 0.69],
        "start_module": "m2",
        "start_lesson": "2.1",
        "xp_bonus": 150,
    },
    {
        "id": "advanced",
        "name": "Продвинутый",
        "name_full": "Опытный инвестор",
        "icon": "🚀",
        "color": "#7c4dff",
        "description": "Отличные знания! Ты готов к продвинутым стратегиям и серьёзному портфелю.",
        "score_range": [0.7, 1.0],
        "start_module": "m3",
        "start_lesson": "3.1",
        "xp_bonus": 300,
    },
]

SEED_ONBOARDING_QUESTIONS = [
    {
        "id": "ob_1", "topic": "stocks", "difficulty": 1, "type": "scenario",
        "scenario": "Твой друг говорит: «Я купил акцию Apple — теперь я владею кусочком компании!»",
        "question": "Прав ли он?",
        "options": ["Да! Акция — это доля в компании", "Нет, акция — это просто бумажка", "Только если он купил больше 50% акций", "Не знаю, что такое акция"],
        "correct_index": 0, "weight": 1.0,
    },
    {
        "id": "ob_2", "topic": "market_logic", "difficulty": 1, "type": "news_reaction",
        "scenario": "Новость: «Tesla отчиталась хуже ожиданий аналитиков»",
        "question": "Что скорее всего произойдёт с акцией Tesla?",
        "options": ["Акция вырастет — компания же прибыльная", "Акция упадёт — результат хуже ожиданий", "Ничего не изменится", "Затрудняюсь ответить"],
        "correct_index": 1, "weight": 1.0,
    },
    {
        "id": "ob_3", "topic": "risk", "difficulty": 2, "type": "decision",
        "scenario": "У тебя 500 000 ₽. Ты вложил ВСЁ в одну акцию — Nvidia. За неделю она упала на 20%.",
        "question": "Какой главный урок из этой ситуации?",
        "options": ["Nvidia — плохая компания, надо было выбрать другую", "Нельзя вкладывать всё в одну акцию — нужна диверсификация", "Надо было продать раньше — нужно следить за рынком каждый час", "Инвестирование — это просто казино"],
        "correct_index": 1, "weight": 1.2,
    },
    {
        "id": "ob_4", "topic": "dividends", "difficulty": 2, "type": "scenario",
        "scenario": "Маша купила акции Сбербанка и каждый год получает деньги на счёт, хотя ничего не продаёт.",
        "question": "Откуда берутся эти деньги?",
        "options": ["Это проценты по вкладу", "Это дивиденды — часть прибыли компании", "Это ошибка банка", "Не знаю"],
        "correct_index": 1, "weight": 1.0,
    },
    {
        "id": "ob_5", "topic": "diversification", "difficulty": 2, "type": "portfolio_choice",
        "scenario": "Тебе нужно выбрать портфель. Какой из них лучше защищён от рисков?",
        "question": "Выбери наиболее диверсифицированный портфель:",
        "options": ["100% в Tesla", "50% Apple + 50% Microsoft", "Apple + Сбербанк + Coca-Cola + Газпром + Nvidia (по 20%)", "Все варианты одинаковы"],
        "correct_index": 2, "weight": 1.2,
    },
    {
        "id": "ob_6", "topic": "etf", "difficulty": 2, "type": "scenario",
        "scenario": "Коля хочет вложить в 500 компаний, но у него нет времени выбирать каждую.",
        "question": "Какой инструмент позволит ему это сделать одной покупкой?",
        "options": ["Банковский вклад", "ETF (биржевой фонд)", "Облигация", "Не знаю, что такое ETF"],
        "correct_index": 1, "weight": 1.0,
    },
    {
        "id": "ob_7", "topic": "portfolio", "difficulty": 3, "type": "analysis",
        "scenario": "Две компании:\n• Сбербанк: P/E = 4.5, дивиденды 9.5%\n• Nvidia: P/E = 70, дивиденды 0.03%",
        "question": "Что означает низкий P/E Сбербанка по сравнению с Nvidia?",
        "options": ["Сбербанк дороже Nvidia", "Акция Сбербанка дешевле относительно прибыли — окупается быстрее", "P/E не имеет значения", "Не знаю, что такое P/E"],
        "correct_index": 1, "weight": 1.5,
    },
    {
        "id": "ob_8", "topic": "market_logic", "difficulty": 3, "type": "crisis",
        "scenario": "Март 2020, COVID. Твой портфель упал на 35% за месяц. Все вокруг в панике.",
        "question": "Какое решение с точки зрения истории было бы лучшим?",
        "options": ["Продать всё, пока не упало ещё больше", "Ничего не делать или докупить — рынок исторически всегда восстанавливался", "Переложить всё в криптовалюту", "Закрыть приложение и забыть"],
        "correct_index": 1, "weight": 1.5,
    },
    {
        "id": "ob_9", "topic": "stocks", "difficulty": 3, "type": "calculation",
        "scenario": "Аня вкладывает 10 000 ₽/мес под 10% годовых. Борис начал на 10 лет позже, но вкладывает 20 000 ₽/мес.",
        "question": "Кто накопит больше к пенсии?",
        "options": ["Борис — он вкладывает больше денег", "Аня — сложный процент и время важнее суммы", "Результат будет одинаковым", "Невозможно сказать без калькулятора"],
        "correct_index": 1, "weight": 1.5,
    },
    {
        "id": "ob_10", "topic": "risk", "difficulty": 3, "type": "emotional",
        "scenario": "Все твои друзья купили акции «хайповой» компании. Она выросла на 300% за месяц. P/E = 500.",
        "question": "Что бы ты сделал?",
        "options": ["Куплю тоже — не хочу упустить!", "Это опасно — P/E 500 говорит о пузыре. Лучше подождать", "Вложу половину — компромисс", "Продам всё остальное и куплю только эту акцию"],
        "correct_index": 1, "weight": 1.5,
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
            "options": [{"text": o} if isinstance(o, str) else o for o in options],
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

    # Learning plan
    learning_plan = []
    for wt in weak_topics:
        learning_plan.append({
            "action": f"Изучить тему «{wt['name']}»",
            "reason": f"Результат {int(wt['score']*100)}% — нужно подтянуть",
            "priority": "focus",
            "topic": wt["id"],
        })
    mid_topics = [x for x in sorted_topics if 0.5 <= x["score"] < 0.7]
    for mt in mid_topics[:2]:
        learning_plan.append({
            "action": f"Закрепить тему «{mt['name']}»",
            "reason": f"Результат {int(mt['score']*100)}% — почти отлично",
            "priority": "high",
            "topic": mt["id"],
        })
    if strong_topics:
        learning_plan.append({
            "action": "Перейти к продвинутым стратегиям",
            "reason": f"Сильные темы: {', '.join(t['name'] for t in strong_topics[:2])}",
            "priority": "normal",
        })
    learning_plan.append({
        "action": "Собрать первый портфель",
        "reason": "Применить знания на практике в симуляторе",
        "priority": "high",
    })

    return {
        "level": level,
        "score": round(normalized, 2),
        "score_pct": round(normalized * 100),
        "topic_scores": topic_scores,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "learning_plan": learning_plan,
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
