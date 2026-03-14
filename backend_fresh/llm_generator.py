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

# Обратный маппинг: "Акции" -> "stocks"
NAME_TO_TOPIC = {}
for _id, _name in TOPIC_NAMES.items():
    NAME_TO_TOPIC[_name] = _id
    NAME_TO_TOPIC[_name.lower()] = _id
    NAME_TO_TOPIC[_id] = _id

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

LESSON_SYSTEM_PROMPT = """Ты — преподаватель финансовой грамотности. Генерируешь персональные уроки для мобильного приложения.

Тебе даны:
- Темы со знаниями пользователя (mastery от 0 до 100%)
- Указание какие темы учить и на каком уровне
- Количество экранов объяснения и вопросов

Генерируй СТРОГО в JSON без markdown. Формат:
{
  "title": "Название урока",
  "screens": [
    {"type": "text", "title": "Заголовок", "content": "Текст..."},
    {"type": "quiz", "title": "Вопрос", "question": "?", "options": ["A","B","C","D"], "correct_index": 0, "explanation": "Почему...", "topic": "topic_id"}
  ]
}

Правила:
- Русский язык
- Объяснения простые, с примерами из жизни и цифрами
- В каждом quiz ровно 4 варианта, 1 правильный
- Неправильные варианты правдоподобные
- У каждого quiz обязательно поле "topic" с id темы
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
    """
    Возвращает список AI-уроков на основе mastery.
    Адаптивность:
    - mastery < 0.3: больше объяснений, лёгкие вопросы
    - mastery 0.3-0.6: меньше объяснений, средние вопросы
    - mastery > 0.6: минимум объяснений, сложные вопросы
    """
    analysis = analyze_mastery(mastery)
    weak = analysis["weak"]
    strong = analysis["strong"]

    stubs = []
    for i, w in enumerate(weak[:5]):
        m = w["mastery"]
        # Адаптивность: чем хуже знает — тем длиннее урок
        if m < 0.3:
            duration = 10
            subtitle = f"Подробное изучение: {w['name']}"
        elif m < 0.6:
            duration = 7
            subtitle = f"Закрепляем: {w['name']}"
        else:
            duration = 5
            subtitle = f"Углубляем: {w['name']}"

        strong_topic = None
        for s in strong:
            if s["id"] != w["id"]:
                strong_topic = s
                break

        stubs.append({
            "id": f"ai_{w['id']}_{i}",
            "title": f"{w['name']}",
            "subtitle": subtitle,
            "duration_min": duration,
            "xp_reward": 35,
            "skill": w["name"],
            "order": i + 1,
            "completed": False,
            "locked": i > 0,  # Только первый разлочен
            "screen_count": 5,
            "generated": True,
            "weak_topic": w["id"],
            "strong_topic": strong_topic["id"] if strong_topic else w["id"],
            "weak_mastery": m,
        })

    return stubs


async def generate_lesson(mastery: dict, weak_topic: str = None, strong_topic: str = None) -> dict | None:
    """
    Генерирует персональный урок через LLM.
    Адаптирует количество объяснений и сложность вопросов по mastery.
    """
    if not OPENROUTER_API_KEY:
        return None

    analysis = analyze_mastery(mastery)

    if not weak_topic and analysis["weak"]:
        weak_topic = analysis["weak"][0]["id"]
    if not strong_topic and analysis["strong"]:
        strong_topic = analysis["strong"][0]["id"]

    if not weak_topic:
        weak_topic = "stocks"
    if not strong_topic:
        strong_topic = weak_topic

    weak_name = TOPIC_NAMES.get(weak_topic, weak_topic)
    strong_name = TOPIC_NAMES.get(strong_topic, strong_topic)
    weak_m = mastery.get(weak_topic, {}).get("mastery", 0.0)
    strong_m = mastery.get(strong_topic, {}).get("mastery", 0.5)

    # Адаптивная структура урока
    if weak_m < 0.3:
        # Совсем не понимает — много объяснений, лёгкие вопросы
        structure = f"""Структура урока (пользователь СОВСЕМ НЕ ПОНИМАЕТ тему "{weak_name}"):
1. 3 текстовых экрана — объясни "{weak_name}" с нуля, очень просто, как ребёнку, с примерами из жизни
2. 2 лёгких вопроса по "{weak_name}" (базовые определения, понятия)
3. 1 итоговый текстовый экран"""
    elif weak_m < 0.6:
        # Понимает базу — меньше теории, средние вопросы
        structure = f"""Структура урока (пользователь ЧАСТИЧНО понимает "{weak_name}"):
1. 2 текстовых экрана — углуби знания по "{weak_name}", дай практические примеры и ситуации
2. 2 вопроса по "{weak_name}" (средней сложности — применение знаний)
3. 1 итоговый текстовый экран"""
    else:
        # Хорошо понимает — минимум теории, сложные вопросы
        structure = f"""Структура урока (пользователь ХОРОШО понимает "{weak_name}"):
1. 1 текстовый экран — продвинутые нюансы "{weak_name}"
2. 2 сложных вопроса по "{weak_name}" (расчёты, анализ, нестандартные ситуации)
3. 1 сложный вопрос по "{strong_name}" (тоже продвинутый)
4. 1 итоговый текстовый экран"""

    # Если есть сильная тема отличная от слабой — добавляем проверочный вопрос
    if strong_topic != weak_topic and weak_m < 0.6:
        structure += f"""
5. Дополнительно: 1 сложный вопрос по сильной теме "{strong_name}" (mastery {int(strong_m*100)}%)"""

    mastery_summary = "Текущие знания пользователя:\n"
    for t_id, t_data in mastery.items():
        name = TOPIC_NAMES.get(t_id, t_id)
        m = t_data.get("mastery", 0.0)
        mastery_summary += f"- {name}: {int(m*100)}%\n"

    user_prompt = f"""{mastery_summary}

{structure}

Сгенерируй урок."""

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
        max_tokens=2500,
    )

    response_text = response.choices[0].message.content.strip()

    try:
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    if "screens" not in data or not isinstance(data["screens"], list):
        return None

    valid_screens = []
    for screen in data["screens"]:
        if screen.get("type") == "text" and screen.get("content"):
            valid_screens.append(screen)
        elif screen.get("type") == "quiz" and all(k in screen for k in ("question", "options", "correct_index")):
            if len(screen["options"]) == 4 and isinstance(screen["correct_index"], int):
                # Нормализуем topic: "Акции" -> "stocks"
                raw_topic = screen.get("topic", "")
                screen["topic"] = NAME_TO_TOPIC.get(raw_topic, NAME_TO_TOPIC.get(raw_topic.lower(), weak_topic)) if raw_topic else weak_topic
                valid_screens.append(screen)

    if len(valid_screens) < 3:
        return None

    lesson_id = f"ai_gen_{uuid.uuid4().hex[:8]}"

    return {
        "id": lesson_id,
        "module_id": "m_ai",
        "title": data.get("title", f"Урок: {weak_name}"),
        "subtitle": f"Изучаем {weak_name}",
        "duration_min": 7 if weak_m < 0.3 else 5,
        "xp_reward": 35,
        "skill": weak_name,
        "skill_topic": weak_topic,
        "order": 1,
        "screens": valid_screens,
        "generated": True,
        "weak_topic": weak_topic,
        "strong_topic": strong_topic,
    }


# ─── Комбинирование статических + AI вопросов ───

def build_hybrid_lesson(mastery: dict, weak_topic: str, strong_topic: str, static_questions: list) -> dict | None:
    """
    Строит урок из статических вопросов + AI-генерации.
    Статика: лёгкие/средние вопросы по теме (если есть).
    AI: сложные вопросы и объяснения (если нужны).
    Возвращает None если нужна полная AI-генерация.
    """
    weak_m = mastery.get(weak_topic, {}).get("mastery", 0.0)

    # Ищем подходящие статические вопросы
    if weak_m < 0.3:
        target_diff = [1]
    elif weak_m < 0.6:
        target_diff = [1, 2]
    else:
        target_diff = [2, 3]

    matching = [q for q in static_questions if q["topic"] == weak_topic and q["difficulty"] in target_diff]

    if not matching:
        return None  # Нет статических → полная AI-генерация

    # Есть статические вопросы — комбинируем
    quiz_screens = []
    for q in matching[:2]:
        quiz_screens.append({
            "type": "quiz",
            "title": "Проверим знания",
            "question": q["question"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "explanation": q.get("explanation", ""),
            "topic": q["topic"],
        })

    # Проверяем: нужен ли AI-вопрос (сложный, которого нет в статике)
    hard_static = [q for q in static_questions if q["topic"] == weak_topic and q["difficulty"] == 3]
    needs_ai = weak_m >= 0.5 and not hard_static

    return {
        "static_screens": quiz_screens,
        "needs_ai_explanation": weak_m < 0.3,  # Нужны AI-объяснения
        "needs_ai_hard_question": needs_ai,      # Нужен AI-сложный вопрос
    }


# ─── Кэширование уроков ───

def save_lesson_cache(db, user_id: str, weak_topic: str, strong_topic: str, lesson: dict):
    """Сохраняет сгенерированный урок в кэш."""
    import json as _json
    db.execute(
        "INSERT OR REPLACE INTO lesson_cache (user_id, weak_topic, strong_topic, lesson_json) VALUES (?,?,?,?)",
        (user_id, weak_topic, strong_topic, _json.dumps(lesson, ensure_ascii=False)),
    )
    db.commit()


def get_cached_lesson(db, user_id: str, weak_topic: str) -> dict | None:
    """Достаёт урок из кэша."""
    import json as _json
    row = db.execute(
        "SELECT lesson_json FROM lesson_cache WHERE user_id=? AND weak_topic=?",
        (user_id, weak_topic),
    ).fetchone()
    if row:
        try:
            return _json.loads(row["lesson_json"])
        except (ValueError, TypeError):
            return None
    return None


def clear_lesson_cache(db, user_id: str, weak_topic: str = None):
    """Удаляет кэш уроков (все или по теме)."""
    if weak_topic:
        db.execute("DELETE FROM lesson_cache WHERE user_id=? AND weak_topic=?", (user_id, weak_topic))
    else:
        db.execute("DELETE FROM lesson_cache WHERE user_id=?", (user_id,))
    db.commit()
