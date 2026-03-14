from datetime import date, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cards import CARDS
from database import get_db, init_db

# Контракт для Назар + Лёша:
# select_next_card(user_id, history, all_cards) -> card dict
# card ОБЯЗАН содержать поле "explanations": list[str] для фронта.
try:
    from ml.selector import select_next_card
except ImportError:  # pragma: no cover - запасной вариант
    import random

    def select_next_card(user_id, history, all_cards):
        return random.choice(all_cards)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/experience")
def get_experience(userId: str):
    db = get_db()
    today = str(date.today())
    rows = db.execute(
        "SELECT card_id, is_correct, difficulty "
        "FROM interactions WHERE user_id=? AND date(created_at)=?",
        (userId, today),
    ).fetchall()
    history = [
        {
            "card_id": r["card_id"],
            "is_correct": bool(r["is_correct"]),
            "difficulty": r["difficulty"],
        }
        for r in rows
    ]
    card = select_next_card(userId, history, CARDS)
    db.close()
    return card


class Interaction(BaseModel):
    userId: str
    cardId: int
    answer_index: int


@app.post("/interactions")
def post_interaction(body: Interaction):
    db = get_db()
    today = str(date.today())

    card = next((c for c in CARDS if c["id"] == body.cardId), None)
    is_correct = bool(card and body.answer_index == card["correct_index"])

    db.execute(
        "INSERT INTO interactions "
        "(user_id, card_id, answer_index, is_correct, difficulty) "
        "VALUES (?,?,?,?,?)",
        (
            body.userId,
            body.cardId,
            body.answer_index,
            int(is_correct),
            card["difficulty"] if card else 1,
        ),
    )

    prog = db.execute(
        "SELECT * FROM progress WHERE user_id=?", (body.userId,)
    ).fetchone()

    if not prog:
        streak = 1 if is_correct else 0
        correct_total = 1 if is_correct else 0
        db.execute(
            "INSERT INTO progress "
            "(user_id, streak, correct_total, last_active_date) "
            "VALUES (?,?,?,?)",
            (body.userId, streak, correct_total, today),
        )
    else:
        streak = prog["streak"]
        correct_total = prog["correct_total"]
        if prog["last_active_date"] != today and is_correct:
            streak += 1
        if is_correct:
            correct_total += 1
        db.execute(
            "UPDATE progress "
            "SET streak=?, correct_total=?, last_active_date=? "
            "WHERE user_id=?",
            (streak, correct_total, today, body.userId),
        )

    db.commit()
    db.close()
    return {
        "is_correct": is_correct,
        "correct_index": card["correct_index"] if card else None,
        "streak": streak,
    }


@app.get("/progress")
def get_progress(userId: str):
    db = get_db()
    prog = db.execute(
        "SELECT * FROM progress WHERE user_id=?", (userId,)
    ).fetchone()
    db.close()
    if not prog:
        return {
            "streak": 0,
            "correct_total": 0,
            "last_active_date": None,
        }
    return dict(prog)


@app.post("/daily")
def new_day():
    return {"ok": True}


class RegisterBody(BaseModel):
    email: str
    name: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/register")
def register(body: RegisterBody):
    db = get_db()
    existing = db.execute("SELECT email FROM users WHERE email=?", (body.email,)).fetchone()
    if existing:
        db.close()
        return {"ok": False, "error": "Пользователь с такой почтой уже существует"}
    db.execute(
        "INSERT INTO users (email, name, password) VALUES (?,?,?)",
        (body.email, body.name, body.password),
    )
    db.commit()
    db.close()
    return {"ok": True, "email": body.email, "name": body.name}


@app.post("/login")
def login(body: LoginBody):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (body.email, body.password),
    ).fetchone()
    db.close()
    if not user:
        return {"ok": False, "error": "Неверная почта или пароль"}
    return {"ok": True, "email": user["email"], "name": user["name"]}


# Уроки: каждый урок = 3 карточки, отсортированные по сложности
SORTED_CARDS = sorted(CARDS, key=lambda c: (c["difficulty"], c["id"]))
LESSONS = []
for i in range(0, len(SORTED_CARDS), 3):
    group = SORTED_CARDS[i : i + 3]
    LESSONS.append(
        {
            "id": i // 3 + 1,
            "card_ids": [c["id"] for c in group],
            "topic": group[0]["topic"],
            "difficulty": max(c["difficulty"] for c in group),
        }
    )


@app.get("/lessons")
def get_lessons(userId: str):
    """Return lessons with lock/complete status. After 2nd lesson, 24h cooldown."""
    db = get_db()
    completions = db.execute(
        "SELECT lesson_id, completed_at FROM lesson_completions WHERE user_id=?",
        (userId,),
    ).fetchall()
    db.close()

    done_map = {}
    for r in completions:
        done_map[r["lesson_id"]] = r["completed_at"]

    now = datetime.utcnow()
    completed_count = 0
    result = []

    for lesson in LESSONS:
        completed_at = done_map.get(lesson["id"])
        is_completed = completed_at is not None

        # Unlock logic
        if lesson["id"] == 1:
            locked = False
            unlock_at = None
        else:
            prev_completed_at = done_map.get(lesson["id"] - 1)
            if prev_completed_at is None:
                locked = True
                unlock_at = None
            elif completed_count >= 2:
                # After 2nd completed lesson, 24h cooldown
                prev_time = datetime.fromisoformat(prev_completed_at)
                unlock_time = prev_time + timedelta(hours=24)
                locked = now < unlock_time
                unlock_at = unlock_time.isoformat() if locked else None
            else:
                locked = False
                unlock_at = None

        if is_completed:
            locked = False
            unlock_at = None

        result.append(
            {
                "id": lesson["id"],
                "card_ids": lesson["card_ids"],
                "topic": lesson["topic"],
                "difficulty": lesson["difficulty"],
                "completed": is_completed,
                "locked": locked,
                "unlock_at": unlock_at,
                "question_count": len(lesson["card_ids"]),
            }
        )

        if is_completed:
            completed_count += 1

    return result


@app.get("/lesson-cards")
def get_lesson_cards(userId: str, lessonId: int):
    """Return the full card data for a lesson's questions."""
    lesson = next((l for l in LESSONS if l["id"] == lessonId), None)
    if not lesson:
        return []
    return [c for c in CARDS if c["id"] in lesson["card_ids"]]


class LessonComplete(BaseModel):
    userId: str
    lessonId: int


@app.post("/complete-lesson")
def complete_lesson(body: LessonComplete):
    db = get_db()
    existing = db.execute(
        "SELECT id FROM lesson_completions WHERE user_id=? AND lesson_id=?",
        (body.userId, body.lessonId),
    ).fetchone()
    if existing:
        db.close()
        return {"ok": True, "duplicate": True}
    db.execute(
        "INSERT INTO lesson_completions (user_id, lesson_id) VALUES (?,?)",
        (body.userId, body.lessonId),
    )
    db.commit()
    db.close()
    return {"ok": True}


@app.get("/daily-cards")
def get_daily_cards(userId: str):
    """Return all cards sorted by difficulty with completion status for today."""
    db = get_db()
    today = str(date.today())
    rows = db.execute(
        "SELECT card_id, is_correct FROM interactions "
        "WHERE user_id=? AND date(created_at)=?",
        (userId, today),
    ).fetchall()
    done_map = {r["card_id"]: bool(r["is_correct"]) for r in rows}
    db.close()

    sorted_cards = sorted(CARDS, key=lambda c: (c["difficulty"], c["id"]))
    result = []
    unlocked = True
    for card in sorted_cards:
        completed = done_map.get(card["id"])
        result.append({
            "id": card["id"],
            "topic": card["topic"],
            "difficulty": card["difficulty"],
            "text": card["text"],
            "locked": not unlocked,
            "completed": completed is not None,
            "correct": completed if completed is not None else None,
        })
        if completed is None:
            unlocked = False
    return result


@app.get("/audit")
def get_audit(userId: str):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM interactions "
        "WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        (userId,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

