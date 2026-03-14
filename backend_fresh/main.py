import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from cards import CARDS
from database import START_BALANCE, get_db, init_db
from lessons_v2 import LESSONS, LESSON_MAP, MODULE_MAP, MODULES, get_lesson, get_module_lessons
from ml.selector import select_next_card
from onboarding import (
    ONBOARDING_LEVELS,
    TOPICS as LEARNING_TOPICS,
    compute_topic_mastery,
    get_strong_topics,
    get_topics_due_for_review,
    get_weak_topics,
    load_onboarding_questions,
    recommend_next_content,
    score_onboarding,
    validate_answers_payload,
)
from stocks import (
    ACHIEVEMENTS,
    ACHIEVEMENT_MAP,
    LEVELS,
    STOCK_MAP,
    STOCKS,
    get_daily_event,
    get_daily_missions,
    get_daily_prices,
    get_level_for_xp,
    get_sparkline,
    get_stock,
)

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-min-32-bytes-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "180"))
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if x.strip()]

app = FastAPI(title="Pulse Fresh Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.exception_handler(HTTPException)
async def http_exc_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exc_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"ok": False, "error": "internal_server_error", "detail": str(exc)})


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def parse_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(authorization: Optional[str] = Header(default=None)) -> str:
    token = parse_bearer_token(authorization)
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid_token: {exc}")
    email = data.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="token_missing_subject")
    return email


def resolve_user_id(user_id_param: Optional[str], current_user: str) -> str:
    if user_id_param and user_id_param != current_user:
        raise HTTPException(status_code=403, detail="user_mismatch")
    return current_user


def add_xp(db, user_id: str, amount: int):
    prog = db.execute("SELECT xp FROM progress WHERE user_id=?", (user_id,)).fetchone()
    if not prog:
        db.execute(
            "INSERT INTO progress (user_id, xp, level, balance) VALUES (?,?,1,?)",
            (user_id, amount, START_BALANCE),
        )
    else:
        new_xp = int(prog["xp"] or 0) + amount
        new_level = get_level_for_xp(new_xp)["current"]["level"]
        db.execute("UPDATE progress SET xp=?, level=? WHERE user_id=?", (new_xp, new_level, user_id))


def unlock_achievement(db, user_id: str, achievement_id: str):
    existing = db.execute(
        "SELECT id FROM user_achievements WHERE user_id=? AND achievement=?",
        (user_id, achievement_id),
    ).fetchone()
    if existing:
        return False
    db.execute("INSERT INTO user_achievements (user_id, achievement) VALUES (?,?)", (user_id, achievement_id))
    ach = ACHIEVEMENT_MAP.get(achievement_id)
    if ach:
        add_xp(db, user_id, int(ach.get("xp_reward", 0)))
    return True


def complete_daily_mission(db, user_id: str, mission_id: str):
    today = str(date.today())
    missions = get_daily_missions(user_id)
    if any(m["id"] == mission_id for m in missions):
        db.execute(
            "INSERT OR REPLACE INTO daily_missions (user_id, mission, completed, date) VALUES (?,?,1,?)",
            (user_id, mission_id, today),
        )


def update_streak(db, user_id: str):
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    prog = db.execute("SELECT streak, last_active_date FROM progress WHERE user_id=?", (user_id,)).fetchone()
    if not prog:
        db.execute(
            "INSERT INTO progress (user_id, streak, last_active_date, balance) VALUES (?,1,?,?)",
            (user_id, today, START_BALANCE),
        )
        return 1
    last = prog["last_active_date"]
    streak = int(prog["streak"] or 0)
    if last == today:
        return streak
    if last == yesterday:
        streak += 1
    else:
        streak = 1
    db.execute("UPDATE progress SET streak=?, last_active_date=? WHERE user_id=?", (streak, today, user_id))
    if streak >= 7:
        unlock_achievement(db, user_id, "streak_7")
    return streak


class RegisterBody(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=256)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


@app.get("/health")
def health():
    db = get_db()
    db.execute("SELECT 1").fetchone()
    db.close()
    return {"ok": True, "status": "healthy", "time": datetime.utcnow().isoformat() + "Z"}


@app.post("/auth/register")
@app.post("/register")
def register(body: RegisterBody):
    db = get_db()
    existing = db.execute("SELECT email FROM users WHERE email=?", (body.email,)).fetchone()
    if existing:
        db.close()
        raise HTTPException(status_code=409, detail="user_already_exists")

    pwd_hash = hash_password(body.password)
    db.execute("INSERT INTO users (email, name, password_hash) VALUES (?,?,?)", (body.email, body.name, pwd_hash))
    db.execute(
        "INSERT OR IGNORE INTO progress (user_id, streak, correct_total, xp, level, balance) VALUES (?,0,0,0,1,?)",
        (body.email, START_BALANCE),
    )
    db.commit()
    db.close()
    token = create_access_token(body.email)
    return {"ok": True, "email": body.email, "name": body.name, "access_token": token, "token_type": "bearer"}


@app.post("/auth/login")
@app.post("/login")
def login(body: LoginBody):
    db = get_db()
    user = db.execute("SELECT email, name, password_hash FROM users WHERE email=?", (body.email,)).fetchone()
    db.close()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    token = create_access_token(user["email"])
    return {"ok": True, "email": user["email"], "name": user["name"], "access_token": token, "token_type": "bearer"}


@app.post("/auth/refresh")
def refresh_token(current_user: str = Depends(get_current_user)):
    return {"ok": True, "access_token": create_access_token(current_user), "token_type": "bearer"}


@app.get("/progress")
def get_progress(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    prog = db.execute("SELECT * FROM progress WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    if not prog:
        return {
            "streak": 0,
            "correct_total": 0,
            "last_active_date": None,
            "xp": 0,
            "level": 1,
            "balance": START_BALANCE,
            "level_info": get_level_for_xp(0),
        }
    xp = int(prog["xp"] or 0)
    return {**dict(prog), "level_info": get_level_for_xp(xp)}


@app.get("/achievements")
def get_achievements(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    unlocked = db.execute(
        "SELECT achievement, unlocked_at FROM user_achievements WHERE user_id=?",
        (user_id,),
    ).fetchall()
    db.close()
    unlocked_map = {r["achievement"]: r["unlocked_at"] for r in unlocked}
    return [{**ach, "unlocked": ach["id"] in unlocked_map, "unlocked_at": unlocked_map.get(ach["id"])} for ach in ACHIEVEMENTS]


@app.get("/stocks")
def stocks(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    prices = get_daily_prices(user_id)
    out = []
    for stock in STOCKS:
        current_price = prices.get(stock["ticker"], stock["price"])
        change_pct = round((current_price - stock["price"]) / stock["price"] * 100, 2)
        out.append({**stock, "current_price": current_price, "change_pct": change_pct, "sparkline": get_sparkline(user_id, stock["ticker"])})
    return out


@app.get("/stock/{ticker}")
def stock_detail(ticker: str, userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    stock = get_stock(ticker)
    if not stock:
        raise HTTPException(status_code=404, detail="stock_not_found")
    prices = get_daily_prices(user_id)
    return {**stock, "current_price": prices.get(stock["ticker"], stock["price"]), "sparkline": get_sparkline(user_id, stock["ticker"], 60)}


@app.get("/portfolio")
def get_portfolio(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    prog = db.execute("SELECT balance FROM progress WHERE user_id=?", (user_id,)).fetchone()
    balance = float(prog["balance"] if prog else START_BALANCE)
    holdings = db.execute(
        "SELECT ticker, shares, avg_price FROM portfolio WHERE user_id=? AND shares > 0",
        (user_id,),
    ).fetchall()
    prices = get_daily_prices(user_id)
    items = []
    total_value = balance
    for h in holdings:
        stock = STOCK_MAP.get(h["ticker"])
        current = float(prices.get(h["ticker"], stock["price"] if stock else 0))
        value = float(h["shares"]) * current
        total_value += value
        cost = float(h["shares"]) * float(h["avg_price"])
        pnl = value - cost
        items.append(
            {
                "ticker": h["ticker"],
                "name": stock["name"] if stock else h["ticker"],
                "shares": float(h["shares"]),
                "avg_price": float(h["avg_price"]),
                "current_price": current,
                "value": round(value, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round((pnl / cost * 100) if cost > 0 else 0, 2),
            }
        )
    db.close()
    return {
        "balance": round(balance, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_value - START_BALANCE, 2),
        "total_pnl_pct": round((total_value - START_BALANCE) / START_BALANCE * 100, 2),
        "holdings": sorted(items, key=lambda x: x["value"], reverse=True),
    }


class TradeBody(BaseModel):
    userId: Optional[str] = None
    ticker: str
    shares: float = Field(gt=0)
    action: str


@app.post("/trade")
def trade(body: TradeBody, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(body.userId, current_user)
    stock = get_stock(body.ticker)
    if not stock:
        raise HTTPException(status_code=404, detail="stock_not_found")
    db = get_db()
    prog = db.execute("SELECT balance FROM progress WHERE user_id=?", (user_id,)).fetchone()
    if not prog:
        db.execute("INSERT INTO progress (user_id, balance) VALUES (?,?)", (user_id, START_BALANCE))
        balance = float(START_BALANCE)
    else:
        balance = float(prog["balance"] or 0)

    price = float(get_daily_prices(user_id).get(body.ticker, stock["price"]))
    total = price * body.shares

    if body.action == "buy":
        if total > balance:
            db.close()
            raise HTTPException(status_code=400, detail="insufficient_funds")
        db.execute("UPDATE progress SET balance=? WHERE user_id=?", (balance - total, user_id))
        existing = db.execute("SELECT shares, avg_price FROM portfolio WHERE user_id=? AND ticker=?", (user_id, body.ticker)).fetchone()
        if existing:
            new_shares = float(existing["shares"]) + body.shares
            new_avg = ((float(existing["shares"]) * float(existing["avg_price"])) + total) / new_shares
            db.execute("UPDATE portfolio SET shares=?, avg_price=? WHERE user_id=? AND ticker=?", (new_shares, new_avg, user_id, body.ticker))
        else:
            db.execute("INSERT INTO portfolio (user_id, ticker, shares, avg_price) VALUES (?,?,?,?)", (user_id, body.ticker, body.shares, price))
        unlock_achievement(db, user_id, "first_buy")
    elif body.action == "sell":
        existing = db.execute("SELECT shares, avg_price FROM portfolio WHERE user_id=? AND ticker=?", (user_id, body.ticker)).fetchone()
        if not existing or float(existing["shares"]) < body.shares:
            db.close()
            raise HTTPException(status_code=400, detail="not_enough_shares")
        db.execute("UPDATE progress SET balance=? WHERE user_id=?", (balance + total, user_id))
        db.execute("UPDATE portfolio SET shares=? WHERE user_id=? AND ticker=?", (float(existing["shares"]) - body.shares, user_id, body.ticker))
    else:
        db.close()
        raise HTTPException(status_code=400, detail="invalid_action")

    db.execute(
        "INSERT INTO transactions (user_id, ticker, action, shares, price, total) VALUES (?,?,?,?,?,?)",
        (user_id, body.ticker, body.action, body.shares, price, total),
    )
    complete_daily_mission(db, user_id, "make_trade")
    add_xp(db, user_id, 10)
    db.commit()
    db.close()
    return {"ok": True, "ticker": body.ticker, "action": body.action, "shares": body.shares, "price": price, "total": round(total, 2)}


@app.get("/market-event")
def market_event(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    return {"event": get_daily_event(user_id)}


class EventActionBody(BaseModel):
    userId: Optional[str] = None
    eventId: str
    action: str


@app.post("/market-event/action")
def market_event_action(body: EventActionBody, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(body.userId, current_user)
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO market_events (user_id, event_id, action, seen) VALUES (?,?,?,1)",
        (user_id, body.eventId, body.action),
    )
    complete_daily_mission(db, user_id, "check_portfolio")
    add_xp(db, user_id, 10)
    db.commit()
    db.close()
    return {"ok": True}


@app.get("/v2/modules")
def v2_modules(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    prog = db.execute("SELECT level FROM progress WHERE user_id=?", (user_id,)).fetchone()
    user_level = int(prog["level"] if prog else 1)
    completed = {r["lesson_id"] for r in db.execute("SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user_id,)).fetchall()}
    db.close()
    out = []
    for module in MODULES:
        lessons = get_module_lessons(module["id"])
        done = sum(1 for l in lessons if l["id"] in completed)
        total = len(lessons)
        out.append(
            {
                **module,
                "completed_count": done,
                "total_lessons": total,
                "progress_pct": round(done / total * 100) if total else 0,
                "locked": user_level < module["required_level"],
            }
        )
    return out


@app.get("/v2/lessons")
def v2_lessons(moduleId: str, userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    completed = {r["lesson_id"] for r in db.execute("SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user_id,)).fetchall()}
    db.close()
    lessons = get_module_lessons(moduleId)
    out = []
    for idx, lesson in enumerate(lessons):
        locked = idx > 0 and lessons[idx - 1]["id"] not in completed
        out.append(
            {
                "id": lesson["id"],
                "title": lesson["title"],
                "subtitle": lesson["subtitle"],
                "duration_min": lesson["duration_min"],
                "xp_reward": lesson["xp_reward"],
                "skill": lesson["skill"],
                "order": lesson["order"],
                "completed": lesson["id"] in completed,
                "locked": locked,
                "screen_count": len(lesson["screens"]),
            }
        )
    return out


@app.get("/v2/lesson/{lessonId}")
def v2_lesson_detail(lessonId: str, userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    lesson = get_lesson(lessonId)
    if not lesson:
        raise HTTPException(status_code=404, detail="lesson_not_found")
    db = get_db()
    completed = db.execute("SELECT id FROM lesson_completions WHERE user_id=? AND lesson_id=?", (user_id, lessonId)).fetchone()
    db.close()
    return {**lesson, "completed": completed is not None}


class CompleteLessonBody(BaseModel):
    userId: Optional[str] = None
    lessonId: str
    correctAnswers: int = 0
    totalQuestions: int = 0


@app.post("/v2/complete-lesson")
def v2_complete_lesson(body: CompleteLessonBody, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(body.userId, current_user)
    lesson = LESSON_MAP.get(body.lessonId)
    if not lesson:
        raise HTTPException(status_code=404, detail="lesson_not_found")
    db = get_db()
    exists = db.execute("SELECT id FROM lesson_completions WHERE user_id=? AND lesson_id=?", (user_id, body.lessonId)).fetchone()
    if exists:
        db.close()
        return {"ok": True, "duplicate": True}
    db.execute("INSERT INTO lesson_completions (user_id, lesson_id, xp_earned) VALUES (?,?,?)", (user_id, body.lessonId, lesson["xp_reward"]))
    if body.correctAnswers > 0:
        db.execute("UPDATE progress SET correct_total = correct_total + ? WHERE user_id=?", (body.correctAnswers, user_id))
    add_xp(db, user_id, int(lesson["xp_reward"]))
    streak = update_streak(db, user_id)
    complete_daily_mission(db, user_id, "complete_lesson")
    unlock_achievement(db, user_id, "first_step")
    db.commit()
    db.close()
    return {"ok": True, "xp_earned": lesson["xp_reward"], "streak": streak}


@app.get("/daily-missions")
def daily_missions(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    today = str(date.today())
    missions = get_daily_missions(user_id)
    db = get_db()
    completed = {r["mission"] for r in db.execute(
        "SELECT mission FROM daily_missions WHERE user_id=? AND date=? AND completed=1",
        (user_id, today),
    ).fetchall()}
    db.close()
    return {"missions": [{**m, "completed": m["id"] in completed} for m in missions], "all_completed": all(m["id"] in completed for m in missions)}


@app.get("/diary")
def diary(limit: int = 20, userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    rows = db.execute("SELECT * FROM diary WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.get("/transactions")
def transactions(limit: int = 30, userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    rows = db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.get("/dashboard")
def dashboard(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    prog = db.execute("SELECT * FROM progress WHERE user_id=?", (user_id,)).fetchone()
    xp = int(prog["xp"] if prog else 0)
    streak = int(prog["streak"] if prog else 0)
    balance = float(prog["balance"] if prog else START_BALANCE)
    total_trades = db.execute("SELECT COUNT(*) AS cnt FROM transactions WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    lessons_done = db.execute("SELECT COUNT(*) AS cnt FROM lesson_completions WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    ach_count = db.execute("SELECT COUNT(*) AS cnt FROM user_achievements WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    onboarding = db.execute("SELECT level_id FROM onboarding_results WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    return {
        "level_info": get_level_for_xp(xp),
        "xp": xp,
        "streak": streak,
        "portfolio": {"balance": balance},
        "stats": {"trades_made": total_trades, "lessons_completed": lessons_done, "achievements": ach_count},
        "onboarding_completed": onboarding is not None,
    }


@app.post("/check-portfolio")
def check_portfolio(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    complete_daily_mission(db, user_id, "check_portfolio")
    update_streak(db, user_id)
    db.commit()
    db.close()
    return {"ok": True}


class FreezeBody(BaseModel):
    userId: Optional[str] = None


@app.post("/buy-freeze")
def buy_freeze(body: FreezeBody, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(body.userId, current_user)
    db = get_db()
    prog = db.execute("SELECT xp FROM progress WHERE user_id=?", (user_id,)).fetchone()
    if not prog or int(prog["xp"] or 0) < 200:
        db.close()
        raise HTTPException(status_code=400, detail="not_enough_xp")
    db.execute("UPDATE progress SET xp = xp - 200 WHERE user_id=?", (user_id,))
    db.execute("INSERT INTO streak_freezes (user_id) VALUES (?)", (user_id,))
    db.commit()
    db.close()
    return {"ok": True}


@app.get("/levels")
def levels():
    return LEVELS


@app.get("/onboarding/questions")
def onboarding_questions():
    db = get_db()
    questions = load_onboarding_questions(db, include_answers=False)
    db.close()
    return {"questions": questions, "total": len(questions)}


@app.get("/onboarding/status")
def onboarding_status(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    result = db.execute(
        "SELECT level_id, score, start_module, start_lesson, completed_at FROM onboarding_results WHERE user_id=?",
        (user_id,),
    ).fetchone()
    db.close()
    if not result:
        return {"completed": False}
    return {
        "completed": True,
        "level_id": result["level_id"],
        "score": result["score"],
        "start_module": result["start_module"],
        "start_lesson": result["start_lesson"],
        "completed_at": result["completed_at"],
    }


class OnboardingSubmitBody(BaseModel):
    userId: Optional[str] = None
    answers: List[Dict[str, Any]]


@app.post("/onboarding/submit")
def onboarding_submit(body: OnboardingSubmitBody, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(body.userId, current_user)
    db = get_db()
    q_with_answers = load_onboarding_questions(db, include_answers=True)
    ok, error = validate_answers_payload(body.answers, q_with_answers)
    if not ok:
        db.close()
        raise HTTPException(status_code=422, detail=error)

    result = score_onboarding(body.answers, q_with_answers)
    db.execute(
        """
        INSERT OR REPLACE INTO onboarding_results
        (user_id, level_id, score, topic_scores, answers_json, start_module, start_lesson)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            user_id,
            result["level"]["id"],
            result["score"],
            json.dumps(result["topic_scores"], ensure_ascii=False),
            json.dumps(body.answers, ensure_ascii=False),
            result["recommended_start"]["module"],
            result["recommended_start"]["lesson"],
        ),
    )
    for detail in result["details"]:
        db.execute(
            "INSERT INTO adaptive_answers (user_id, topic, question_id, is_correct, time_ms, source) VALUES (?,?,?,?,?,?)",
            (user_id, detail["topic"], detail["question_id"], int(detail["is_correct"]), int(detail.get("time_ms", 0)), "onboarding"),
        )
    db.execute("UPDATE progress SET investor_type=? WHERE user_id=?", (result["level"]["id"], user_id))
    add_xp(db, user_id, int(result["xp_bonus"]))
    db.commit()
    db.close()
    return {"ok": True, **result}


@app.get("/onboarding/result")
def onboarding_result(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    row = db.execute("SELECT * FROM onboarding_results WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    if not row:
        return {"ok": False}
    level = next((l for l in ONBOARDING_LEVELS if l["id"] == row["level_id"]), ONBOARDING_LEVELS[0])
    try:
        topic_scores = json.loads(row["topic_scores"]) if row["topic_scores"] else {}
    except (json.JSONDecodeError, TypeError):
        topic_scores = {}
    return {
        "ok": True,
        "level": level,
        "score": row["score"],
        "topic_scores": topic_scores,
        "start_module": row["start_module"],
        "start_lesson": row["start_lesson"],
    }


@app.get("/adaptive/mastery")
def adaptive_mastery(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    mastery = compute_topic_mastery(db, user_id)
    db.close()
    return {"mastery": mastery, "weak_topics": get_weak_topics(mastery), "strong_topics": get_strong_topics(mastery)}


@app.get("/adaptive/recommendation")
def adaptive_recommendation(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    mastery = compute_topic_mastery(db, user_id)
    rec = recommend_next_content(db, user_id, mastery)
    due = get_topics_due_for_review(db, user_id, mastery)
    db.close()
    return {"recommendation": rec, "review_due": due[:3]}


class AdaptiveAnswerBody(BaseModel):
    userId: Optional[str] = None
    topic: str
    questionId: str = ""
    isCorrect: bool
    timeMs: int = 0
    source: str = "lesson"


@app.post("/adaptive/answer")
def adaptive_answer(body: AdaptiveAnswerBody, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(body.userId, current_user)
    if body.topic not in {t["id"] for t in LEARNING_TOPICS}:
        raise HTTPException(status_code=422, detail="invalid_topic")
    db = get_db()
    db.execute(
        "INSERT INTO adaptive_answers (user_id, topic, question_id, is_correct, time_ms, source) VALUES (?,?,?,?,?,?)",
        (user_id, body.topic, body.questionId, int(body.isCorrect), int(body.timeMs), body.source),
    )
    mastery = compute_topic_mastery(db, user_id)
    topic_data = mastery.get(body.topic, {"mastery": 0.0, "answers": 0})
    db.execute(
        "INSERT OR REPLACE INTO topic_mastery (user_id, topic, mastery, answers, updated_at) VALUES (?,?,?,?,datetime('now'))",
        (user_id, body.topic, float(topic_data["mastery"]), int(topic_data["answers"])),
    )
    db.commit()
    db.close()
    return {"ok": True, "mastery": topic_data["mastery"]}


@app.get("/ml/features/{userId}")
def ml_features(userId: str, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    onboarding_row = db.execute("SELECT topic_scores, score FROM onboarding_results WHERE user_id=?", (user_id,)).fetchone()
    adaptive_rows = db.execute(
        "SELECT topic, is_correct, time_ms FROM adaptive_answers WHERE user_id=? ORDER BY created_at DESC LIMIT 500",
        (user_id,),
    ).fetchall()
    prog = db.execute("SELECT streak, xp, level FROM progress WHERE user_id=?", (user_id,)).fetchone()
    db.close()

    topic_scores = {}
    if onboarding_row and onboarding_row["topic_scores"]:
        try:
            topic_scores = json.loads(onboarding_row["topic_scores"])
        except (json.JSONDecodeError, TypeError):
            topic_scores = {}

    per_topic = {}
    total_correct = 0
    total_answers = 0
    total_time = 0
    for row in adaptive_rows:
        t = row["topic"]
        per_topic.setdefault(t, {"answers": 0, "correct": 0, "avg_time_ms": 0})
        per_topic[t]["answers"] += 1
        per_topic[t]["correct"] += int(row["is_correct"])
        total_answers += 1
        total_correct += int(row["is_correct"])
        total_time += int(row["time_ms"] or 0)
    for t, data in per_topic.items():
        data["accuracy"] = round(data["correct"] / data["answers"], 4) if data["answers"] else 0.0
        data["avg_time_ms"] = round(total_time / total_answers, 2) if total_answers else 0

    features = {
        "user_id": user_id,
        "onboarding_score": float(onboarding_row["score"]) if onboarding_row else None,
        "topic_scores": topic_scores,
        "adaptive_answers_count": total_answers,
        "adaptive_accuracy": round(total_correct / total_answers, 4) if total_answers else 0.0,
        "avg_answer_time_ms": round(total_time / total_answers, 2) if total_answers else 0.0,
        "per_topic": per_topic,
        "streak": int(prog["streak"] if prog else 0),
        "xp": int(prog["xp"] if prog else 0),
        "level": int(prog["level"] if prog else 1),
    }
    return {"ok": True, "features": features, "schema_version": "1.0.0"}


class PredictLevelBody(BaseModel):
    userId: Optional[str] = None
    features_override: Optional[Dict[str, Any]] = None


@app.post("/ml/predict-level")
def ml_predict_level(body: PredictLevelBody, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(body.userId, current_user)
    features_resp = ml_features(user_id, current_user)
    features = dict(features_resp["features"])
    if body.features_override:
        features.update(body.features_override)

    score = 0.0
    onboarding_score = features.get("onboarding_score")
    if onboarding_score is not None:
        score += float(onboarding_score) * 0.5
    score += float(features.get("adaptive_accuracy", 0.0)) * 0.3
    score += min(float(features.get("level", 1)) / 5.0, 1.0) * 0.2

    if score < 0.4:
        level = "novice"
    elif score < 0.7:
        level = "basic"
    else:
        level = "advanced"
    confidence = round(min(max(score, 0.0), 1.0), 3)

    return {
        "ok": True,
        "user_id": user_id,
        "predicted_level": level,
        "confidence": confidence,
        "model_version": "rule-based-v1",
        "feature_snapshot": features,
    }


@app.get("/experience")
def experience(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    today = str(date.today())
    rows = db.execute(
        "SELECT card_id, is_correct, difficulty FROM interactions WHERE user_id=? AND date(created_at)=?",
        (user_id, today),
    ).fetchall()
    history = [{"card_id": r["card_id"], "is_correct": bool(r["is_correct"]), "difficulty": r["difficulty"]} for r in rows]
    card = select_next_card(user_id, history, CARDS)
    db.close()
    return card


class InteractionBody(BaseModel):
    userId: Optional[str] = None
    cardId: int
    answer_index: int


@app.post("/interactions")
def interactions(body: InteractionBody, current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(body.userId, current_user)
    card = next((c for c in CARDS if c["id"] == body.cardId), None)
    if not card:
        raise HTTPException(status_code=404, detail="card_not_found")
    is_correct = bool(body.answer_index == card["correct_index"])
    db = get_db()
    db.execute(
        "INSERT INTO interactions (user_id, card_id, answer_index, is_correct, difficulty) VALUES (?,?,?,?,?)",
        (user_id, body.cardId, body.answer_index, int(is_correct), int(card.get("difficulty", 1))),
    )
    if is_correct:
        db.execute("UPDATE progress SET correct_total = correct_total + 1 WHERE user_id=?", (user_id,))
        add_xp(db, user_id, 15)
    db.commit()
    db.close()
    return {"is_correct": is_correct, "correct_index": card["correct_index"]}


@app.get("/audit")
def audit(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    rows = db.execute("SELECT * FROM interactions WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]
