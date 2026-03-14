"""
Генерация адаптивных вопросов и уроков через OpenRouter API.
Использует mastery пользователя для выбора темы и сложности.
"""

import json
import os
import uuid
from openai import OpenAI

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = "arcee-ai/trinity-large-preview:free"

TOPIC_NAMES = {
    "stocks": "Акции",
    "market_logic": "Логика рынка",
    "risk": "Риск и управление рисками",
    "dividends": "Дивиденды",
    "diversification": "Диверсификация",
    "etf": "ETF и фонды",
    "portfolio": "Портфель и управление портфелем",
}

DIFFICULTY_LABELS = {
    1: "лёгкий (базовые понятия, определения)",
    2: "средний (применение знаний, анализ ситуаций)",
    3: "сложный (продвинутые концепции, расчёты, нестандартные ситуации)",
}

SYSTEM_PROMPT = """Ты — преподаватель финансовой грамотности и инвестиций.
Твоя задача — генерировать учебные вопросы с вариантами ответов для мобильного приложения,
которое обучает людей инвестициям.

Правила:
1. Вопрос должен быть на русском языке
2. Ровно 4 варианта ответа
3. Только один правильный ответ
4. Неправильные варианты должны быть правдоподобными, но чётко неверными
5. Объяснение должно быть коротким (1-2 предложения) и понятным
6. Вопросы должны быть практичными и полезными для начинающего инвестора
7. Не повторяй вопросы, которые уже были заданы (они указаны ниже)

Ответ СТРОГО в JSON формате, без markdown:
{
  "question": "Текст вопроса",
  "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
  "correct_index": 0,
  "explanation": "Краткое объяснение правильного ответа"
}"""


def select_topic_and_difficulty(mastery: dict) -> tuple[str, int]:
    """
    Выбирает тему и сложность на основе mastery пользователя.
    Приоритет — слабые темы (низкий mastery).
    """
    topic_scores = []
    for topic_id, topic_data in mastery.items():
        m = topic_data.get("mastery", 0.0)
        answers = topic_data.get("answers", 0)
        priority = (1.0 - m) + (0.2 if answers < 3 else 0.0)
        topic_scores.append((topic_id, m, priority))

    topic_scores.sort(key=lambda x: x[2], reverse=True)

    if not topic_scores:
        return "stocks", 1

    topic_id, m, _ = topic_scores[0]

    if m < 0.3:
        difficulty = 1
    elif m < 0.6:
        difficulty = 2
    else:
        difficulty = 3

    return topic_id, difficulty


def get_recent_questions(db, user_id: str, topic: str, limit: int = 10) -> list[str]:
    """Получает тексты недавних вопросов, чтобы не повторяться."""
    from adaptive_questions import ADAPTIVE_QUESTIONS

    recent = db.execute(
        "SELECT question_id FROM adaptive_answers WHERE user_id=? AND topic=? ORDER BY created_at DESC LIMIT ?",
        (user_id, topic, limit),
    ).fetchall()

    recent_ids = [r["question_id"] for r in recent]
    recent_texts = []
    for q in ADAPTIVE_QUESTIONS:
        if q["id"] in recent_ids:
            recent_texts.append(q["question"])

    return recent_texts


async def generate_question(topic: str, difficulty: int, recent_questions: list[str] = None) -> dict | None:
    """
    Генерирует вопрос через OpenRouter API (Qwen).
    Возвращает dict с полями: id, topic, difficulty, question, options, correct_index, explanation.
    """
    if not OPENROUTER_API_KEY:
        return None

    recent_questions = recent_questions or []
    topic_name = TOPIC_NAMES.get(topic, topic)
    diff_label = DIFFICULTY_LABELS.get(difficulty, "средний")

    user_prompt = f"Сгенерируй один вопрос по теме \"{topic_name}\", уровень сложности: {diff_label}."

    if recent_questions:
        user_prompt += "\n\nНе повторяй эти вопросы:\n"
        for q in recent_questions[:10]:
            user_prompt += f"- {q}\n"

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=500,
    )

    response_text = response.choices[0].message.content.strip()

    # Парсим JSON из ответа
    try:
        # Убираем возможные markdown-обёртки
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]

        data = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    # Валидация
    if not all(k in data for k in ("question", "options", "correct_index", "explanation")):
        return None
    if len(data["options"]) != 4:
        return None
    if not isinstance(data["correct_index"], int) or data["correct_index"] not in range(4):
        return None

    question_id = f"gen_{uuid.uuid4().hex[:8]}"

    return {
        "id": question_id,
        "topic": topic,
        "difficulty": difficulty,
        "question": data["question"],
        "options": data["options"],
        "correct_index": data["correct_index"],
        "explanation": data["explanation"],
        "generated": True,
    }


# ─── Генерация полных уроков ───

LESSON_SYSTEM_PROMPT = """Ты — преподаватель финансовой грамотности. Генерируешь уроки для мобильного приложения.

Тебе дан список тем с уровнем знаний пользователя (mastery от 0.0 до 1.0).
Слабые темы (mastery < 0.5) — пользователь плохо знает, нужно объяснить просто.
Сильные темы (mastery >= 0.7) — пользователь хорошо знает, можно дать сложный вопрос.

Сгенерируй урок в виде JSON-массива экранов. Урок должен содержать:
1. 2 текстовых экрана с понятным объяснением СЛАБОЙ темы (простым языком, с примерами)
2. 1 лёгкий вопрос по слабой теме (чтобы закрепить)
3. 1 сложный вопрос по сильной теме (чтобы углубить знания)
4. 1 итоговый текстовый экран с кратким выводом

Формат СТРОГО JSON без markdown:
{
  "title": "Название урока",
  "screens": [
    {"type": "text", "title": "Заголовок", "content": "Текст объяснения..."},
    {"type": "text", "title": "Заголовок", "content": "Текст..."},
    {"type": "quiz", "title": "Проверим", "question": "Вопрос?", "options": ["A","B","C","D"], "correct_index": 0, "explanation": "Почему..."},
    {"type": "quiz", "title": "Сложный вопрос", "question": "Вопрос?", "options": ["A","B","C","D"], "correct_index": 0, "explanation": "Почему..."},
    {"type": "text", "title": "Итог", "content": "Вывод..."}
  ]
}

Правила:
- Русский язык
- Объяснения простые, с реальными примерами и цифрами
- В каждом вопросе ровно 4 варианта, 1 правильный
- Неправильные варианты правдоподобные
- Весь контент про инвестиции и финансы"""


def analyze_mastery(mastery: dict) -> dict:
    """Анализирует mastery и возвращает слабые/сильные темы."""
    weak = []
    strong = []
    for topic_id, data in mastery.items():
        m = data.get("mastery", 0.0)
        answers = data.get("answers", 0)
        name = TOPIC_NAMES.get(topic_id, topic_id)
        entry = {"id": topic_id, "name": name, "mastery": m, "answers": answers}
        if m < 0.5:
            weak.append(entry)
        elif m >= 0.7 and answers >= 2:
            strong.append(entry)

    weak.sort(key=lambda x: x["mastery"])
    strong.sort(key=lambda x: x["mastery"], reverse=True)

    # Если нет слабых — берём тему с наименьшим mastery
    if not weak and mastery:
        all_topics = sorted(mastery.items(), key=lambda x: x[1].get("mastery", 0))
        t_id, t_data = all_topics[0]
        weak = [{"id": t_id, "name": TOPIC_NAMES.get(t_id, t_id), "mastery": t_data.get("mastery", 0), "answers": t_data.get("answers", 0)}]

    # Если нет сильных — берём тему с наибольшим mastery
    if not strong and mastery:
        all_topics = sorted(mastery.items(), key=lambda x: x[1].get("mastery", 0), reverse=True)
        t_id, t_data = all_topics[0]
        if t_id != weak[0]["id"]:
            strong = [{"id": t_id, "name": TOPIC_NAMES.get(t_id, t_id), "mastery": t_data.get("mastery", 0), "answers": t_data.get("answers", 0)}]

    return {"weak": weak, "strong": strong}


def get_lesson_stubs(mastery: dict) -> list[dict]:
    """Возвращает список заглушек для AI-уроков на основе mastery."""
    analysis = analyze_mastery(mastery)
    weak = analysis["weak"]
    strong = analysis["strong"]

    stubs = []
    # Генерируем заглушку для каждой слабой темы (макс 3)
    for i, w in enumerate(weak[:3]):
        strong_topic = strong[0] if strong else None
        weak_name = w["name"]
        strong_name = strong_topic["name"] if strong_topic else ""
        subtitle = f"Изучаем: {weak_name}"
        if strong_name:
            subtitle += f" + проверяем: {strong_name}"

        stubs.append({
            "id": f"ai_{w['id']}_{i}",
            "title": f"Урок: {weak_name}",
            "subtitle": subtitle,
            "duration_min": 7,
            "xp_reward": 35,
            "skill": weak_name,
            "order": i + 1,
            "completed": False,
            "locked": False,
            "screen_count": 5,
            "generated": True,
            "weak_topic": w["id"],
            "strong_topic": strong_topic["id"] if strong_topic else w["id"],
        })

    return stubs


async def generate_lesson(mastery: dict, weak_topic: str = None, strong_topic: str = None) -> dict | None:
    """
    Генерирует полный урок через LLM.
    - weak_topic: тема для обучения (лёгкое объяснение + лёгкий вопрос)
    - strong_topic: тема для проверки (сложный вопрос)
    """
    if not OPENROUTER_API_KEY:
        return None

    analysis = analyze_mastery(mastery)

    if not weak_topic and analysis["weak"]:
        weak_topic = analysis["weak"][0]["id"]
    if not strong_topic and analysis["strong"]:
        strong_topic = analysis["strong"][0]["id"]

    # Fallback
    if not weak_topic:
        weak_topic = "stocks"
    if not strong_topic:
        strong_topic = weak_topic

    weak_name = TOPIC_NAMES.get(weak_topic, weak_topic)
    strong_name = TOPIC_NAMES.get(strong_topic, strong_topic)
    weak_mastery = mastery.get(weak_topic, {}).get("mastery", 0.0)
    strong_mastery = mastery.get(strong_topic, {}).get("mastery", 0.5)

    mastery_summary = "Знания пользователя:\n"
    for t_id, t_data in mastery.items():
        name = TOPIC_NAMES.get(t_id, t_id)
        m = t_data.get("mastery", 0.0)
        level = "слабо" if m < 0.3 else "средне" if m < 0.6 else "хорошо" if m < 0.8 else "отлично"
        mastery_summary += f"- {name}: {int(m*100)}% ({level})\n"

    user_prompt = f"""{mastery_summary}

Слабая тема для обучения: "{weak_name}" (mastery {int(weak_mastery*100)}%) — объясни просто, с примерами из жизни.
Сильная тема для проверки: "{strong_name}" (mastery {int(strong_mastery*100)}%) — дай сложный вопрос.

Сгенерируй урок по этим данным."""

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": LESSON_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2000,
    )

    response_text = response.choices[0].message.content.strip()

    # Парсим JSON
    try:
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    if "screens" not in data or not isinstance(data["screens"], list):
        return None

    # Валидация экранов
    valid_screens = []
    for screen in data["screens"]:
        if screen.get("type") == "text" and screen.get("content"):
            valid_screens.append(screen)
        elif screen.get("type") == "quiz" and all(k in screen for k in ("question", "options", "correct_index")):
            if len(screen["options"]) == 4 and isinstance(screen["correct_index"], int):
                valid_screens.append(screen)

    if len(valid_screens) < 3:
        return None

    lesson_id = f"ai_gen_{uuid.uuid4().hex[:8]}"

    return {
        "id": lesson_id,
        "module_id": "m_ai",
        "title": data.get("title", f"Урок: {weak_name}"),
        "subtitle": f"Изучаем {weak_name}, проверяем {strong_name}",
        "duration_min": 7,
        "xp_reward": 35,
        "skill": weak_name,
        "skill_topic": weak_topic,
        "order": 1,
        "screens": valid_screens,
        "generated": True,
        "weak_topic": weak_topic,
        "strong_topic": strong_topic,
    }
