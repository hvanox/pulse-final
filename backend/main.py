from datetime import date

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

    existing = db.execute(
        "SELECT id FROM interactions "
        "WHERE user_id=? AND card_id=? AND date(created_at)=?",
        (body.userId, body.cardId, today),
    ).fetchone()
    if existing:
        prog = db.execute(
            "SELECT * FROM progress WHERE user_id=?", (body.userId,)
        ).fetchone()
        db.close()
        return {
            "is_correct": None,
            "correct_index": None,
            "streak": prog["streak"] if prog else 0,
            "duplicate": True,
        }

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

