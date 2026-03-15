"""
Генерация адаптивных вопросов и уроков через OpenRouter API.
Использует mastery пользователя для выбора темы и сложности.
"""

import json
import os
import uuid
from openai import AsyncOpenAI

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

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    response = await client.chat.completions.create(
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


def get_lesson_stubs(mastery: dict, completed_ids: set = None) -> list[dict]:
    """
    ВСЕ темы получают уроки:
    - Слабые (mastery < 0.5): из БД (лёгкие), потом ИИ генерирует следующие
    - Сильные (mastery >= 0.5): ИИ генерирует сложные уроки
    Пройденные показываются с галочкой.
    """
    completed_ids = completed_ids or set()

    # Считаем пройденные AI-уроки по темам
    completed_per_topic = {}
    for cid in completed_ids:
        if cid.startswith("ai_") and not cid.startswith("ai_gen_"):
            parts = cid.split("_")
            if len(parts) >= 3:
                topic = "_".join(parts[1:-1])  # для topic вроде market_logic
                idx = int(parts[-1]) if parts[-1].isdigit() else 0
                completed_per_topic[topic] = max(completed_per_topic.get(topic, 0), idx + 1)

    # Сортируем все темы: слабые первыми, сильные потом
    all_topics = []
    for topic_id, data in mastery.items():
        m = data.get("mastery", 0.0)
        name = TOPIC_NAMES.get(topic_id, topic_id)
        all_topics.append({"id": topic_id, "name": name, "mastery": m})
    all_topics.sort(key=lambda x: x["mastery"])

    # Если mastery пустой — все темы
    if not all_topics:
        for tid, tname in TOPIC_NAMES.items():
            all_topics.append({"id": tid, "name": tname, "mastery": 0.0})

    stubs = []

    # 1. Пройденные уроки (с галочкой)
    for topic, count in completed_per_topic.items():
        for idx in range(count):
            stub_id = f"ai_{topic}_{idx}"
            name = TOPIC_NAMES.get(topic, topic)
            stubs.append({
                "id": stub_id,
                "title": name,
                "subtitle": "Пройдено",
                "duration_min": 5,
                "xp_reward": 35,
                "skill": name,
                "order": len(stubs) + 1,
                "completed": True,
                "locked": False,
                "screen_count": 5,
                "generated": True,
                "weak_topic": topic,
                "strong_topic": topic,
                "weak_mastery": mastery.get(topic, {}).get("mastery", 0.5),
            })

    # 2. Новые уроки по ВСЕМ темам
    for t in all_topics:
        m = t["mastery"]
        idx = completed_per_topic.get(t["id"], 0)
        stub_id = f"ai_{t['id']}_{idx}"

        if stub_id in completed_ids:
            continue

        if m < 0.3:
            subtitle = f"Изучаем с нуля: {t['name']}"
            duration = 10
        elif m < 0.5:
            subtitle = f"Закрепляем: {t['name']}"
            duration = 7
        elif m < 0.7:
            subtitle = f"Углубляем: {t['name']}"
            duration = 6
        else:
            subtitle = f"Продвинутый уровень: {t['name']}"
            duration = 5

        # Для сильных тем — strong_topic = сама тема (сложные вопросы)
        # Для слабых — strong_topic = самая сильная другая тема
        if m >= 0.5:
            strong_topic = t["id"]
        else:
            strong_topic = t["id"]
            for other in reversed(all_topics):
                if other["id"] != t["id"] and other["mastery"] >= 0.5:
                    strong_topic = other["id"]
                    break

        stubs.append({
            "id": stub_id,
            "title": t["name"],
            "subtitle": subtitle,
            "duration_min": duration,
            "xp_reward": 35,
            "skill": t["name"],
            "order": len(stubs) + 1,
            "completed": False,
            "locked": False,
            "screen_count": 5,
            "generated": True,
            "weak_topic": t["id"],
            "strong_topic": strong_topic,
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

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    response = await client.chat.completions.create(
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

def _mastery_key(mastery: dict, topic: str) -> str:
    """Создаёт ключ mastery для темы (чтобы понять изменилось ли)."""
    m = mastery.get(topic, {}).get("mastery", 0.0)
    answers = mastery.get(topic, {}).get("answers", 0)
    return f"{m:.2f}_{answers}"


def save_lesson_cache(db, user_id: str, weak_topic: str, strong_topic: str, lesson: dict, mastery: dict = None):
    """Сохраняет сгенерированный урок в кэш."""
    import json as _json
    snap = _mastery_key(mastery, weak_topic) if mastery else ""
    db.execute(
        "INSERT OR REPLACE INTO lesson_cache (user_id, weak_topic, strong_topic, lesson_json, mastery_snapshot) VALUES (?,?,?,?,?)",
        (user_id, weak_topic, strong_topic, _json.dumps(lesson, ensure_ascii=False), snap),
    )
    db.commit()


def get_cached_lesson(db, user_id: str, weak_topic: str, mastery: dict = None) -> dict | None:
    """
    Достаёт урок из кэша.
    Если mastery изменился — кэш невалиден, возвращает None.
    """
    import json as _json
    row = db.execute(
        "SELECT lesson_json, mastery_snapshot FROM lesson_cache WHERE user_id=? AND weak_topic=?",
        (user_id, weak_topic),
    ).fetchone()
    if not row:
        return None

    # Проверяем: mastery изменился?
    if mastery:
        current_snap = _mastery_key(mastery, weak_topic)
        saved_snap = row["mastery_snapshot"] or ""
        if saved_snap and current_snap != saved_snap:
            # Mastery изменился — кэш устарел
            return None

    try:
        return _json.loads(row["lesson_json"])
    except (ValueError, TypeError):
        return None


def invalidate_stale_cache(db, user_id: str, mastery: dict):
    """Удаляет только устаревшие уроки (mastery изменился)."""
    rows = db.execute(
        "SELECT weak_topic, mastery_snapshot FROM lesson_cache WHERE user_id=?",
        (user_id,),
    ).fetchall()
    for row in rows:
        topic = row["weak_topic"]
        saved = row["mastery_snapshot"] or ""
        current = _mastery_key(mastery, topic)
        if saved and current != saved:
            db.execute("DELETE FROM lesson_cache WHERE user_id=? AND weak_topic=?", (user_id, topic))
    db.commit()


def clear_lesson_cache(db, user_id: str, weak_topic: str = None):
    """Удаляет кэш уроков (все или по теме)."""
    if weak_topic:
        db.execute("DELETE FROM lesson_cache WHERE user_id=? AND weak_topic=?", (user_id, weak_topic))
    else:
        db.execute("DELETE FROM lesson_cache WHERE user_id=?", (user_id,))
    db.commit()
