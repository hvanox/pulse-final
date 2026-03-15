import json
import os
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.adaptive_engine import get_default_engine
from adaptive_questions import get_adaptive_question, get_questions_for_lesson, ADAPTIVE_QUESTIONS
from llm_generator import (
    generate_question, generate_lesson, select_topic_and_difficulty,
    get_recent_questions, get_lesson_stubs, analyze_mastery,
    save_lesson_cache, get_cached_lesson, clear_lesson_cache, invalidate_stale_cache,
)
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


# ML Adaptive Engine (singleton)
ml_engine = get_default_engine()

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
    except (ValueError, Exception):
        # Fallback: plain-text comparison for legacy users
        return password == password_hash


def create_access_token(email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """Extract user from JWT token if present. Returns None if no token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return data.get("sub")
    except jwt.PyJWTError:
        return None


def resolve_user_id(user_id_param: Optional[str], current_user: Optional[str]) -> str:
    """Resolve user ID: prefer JWT user, fallback to userId query param."""
    if current_user:
        return current_user
    if user_id_param:
        return user_id_param
    raise HTTPException(status_code=401, detail="userId is required")


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
    email: str = Field(min_length=3, max_length=200)
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class LoginBody(BaseModel):
    email: str
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
    """Все уроки генерируются ЛЛМ на основе mastery пользователя."""
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    mastery = ml_engine.compute_mastery_from_db(db, user_id)
    completed = {r["lesson_id"] for r in db.execute("SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user_id,)).fetchall()}
    db.close()
    ai_stubs = get_lesson_stubs(mastery, completed)

    # Один модуль — всё обучение персональное
    return [{
        "id": "m_ai",
        "title": "Твоё обучение",
        "icon": "🧠",
        "required_level": 1,
        "completed_count": 0,
        "total_lessons": len(ai_stubs),
        "progress_pct": 0,
        "locked": False,
        "generated": True,
    }]


@app.get("/v2/lessons")
def v2_lessons(moduleId: str, userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    """Статические уроки отсортированы по слабым темам из онбординга, потом AI-уроки."""
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    completed = {r["lesson_id"] for r in db.execute("SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user_id,)).fetchall()}
    mastery = ml_engine.compute_mastery_from_db(db, user_id)

    # Получаем результаты онбординга — какие темы слабые
    onboarding_row = db.execute("SELECT topic_scores FROM onboarding_results WHERE user_id=?", (user_id,)).fetchone()
    db.close()

    topic_weakness = {}  # topic_id -> score (0=слабый, 1=сильный)
    if onboarding_row and onboarding_row["topic_scores"]:
        try:
            topic_scores = json.loads(onboarding_row["topic_scores"])
            for topic_id, data in topic_scores.items():
                score = data.get("score", data.get("mastery", 0.5)) if isinstance(data, dict) else 0.5
                topic_weakness[topic_id] = score
        except (json.JSONDecodeError, TypeError):
            pass

    # Собираем все статические уроки
    all_static = []
    for module in MODULES:
        for lesson in get_module_lessons(module["id"]):
            topic = lesson.get("skill_topic", "stocks")
            weakness = topic_weakness.get(topic, 0.5)
            # Также учитываем текущий mastery
            current_m = mastery.get(topic, {}).get("mastery", weakness)
            # Комбинируем: онбординг + текущий mastery (слабые первыми)
            combined_score = (weakness + current_m) / 2
            all_static.append({
                **lesson,
                "_sort_score": combined_score,
            })

    # Сортируем: слабые темы первыми
    all_static.sort(key=lambda x: x["_sort_score"])

    out = []
    for order, lesson in enumerate(all_static, 1):
        is_completed = lesson["id"] in completed
        is_locked = order > 1 and not out[-1].get("completed", False)
        out.append({
            "id": lesson["id"],
            "title": lesson["title"],
            "subtitle": lesson["subtitle"],
            "duration_min": lesson["duration_min"],
            "xp_reward": lesson["xp_reward"],
            "skill": lesson["skill"],
            "order": order,
            "completed": is_completed,
            "locked": is_locked,
            "screen_count": len(lesson["screens"]),
            "generated": False,
        })

    # Все статические пройдены?
    all_static_done = all(l["completed"] for l in out)

    # AI-уроки — после статических, тоже на основе mastery
    ai_stubs = get_lesson_stubs(mastery, completed)
    for stub in ai_stubs:
        order = len(out) + 1
        stub["order"] = order
        stub["locked"] = not all_static_done
        out.append(stub)

    return out


@app.get("/v2/generate-lesson")
async def v2_generate_lesson(
    weakTopic: Optional[str] = Query(default=None),
    strongTopic: Optional[str] = Query(default=None),
    userId: Optional[str] = Query(default=None),
    current_user: str = Depends(get_current_user),
):
    """Отдаёт урок из кэша или генерирует на лету."""
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    mastery = ml_engine.compute_mastery_from_db(db, user_id)

    # 1. Пробуем кэш (урок хранится, пока mastery не изменится)
    if weakTopic:
        cached = get_cached_lesson(db, user_id, weakTopic, mastery)
        if cached:
            db.close()
            return {**cached, "completed": False}

    db.close()

    # 2. Нет кэша — генерируем на лету и сохраняем
    lesson = await generate_lesson(mastery, weakTopic, strongTopic)
    if not lesson:
        raise HTTPException(status_code=500, detail="lesson_generation_failed")

    # Сохраняем в кэш
    db2 = get_db()
    save_lesson_cache(db2, user_id, weakTopic or lesson.get("weak_topic", "stocks"), strongTopic or lesson.get("strong_topic", "stocks"), lesson, mastery)
    db2.close()

    return {**lesson, "completed": False}


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
    xp_reward = 35  # дефолт для AI-уроков

    if lesson:
        xp_reward = int(lesson["xp_reward"])

    db = get_db()
    exists = db.execute("SELECT id FROM lesson_completions WHERE user_id=? AND lesson_id=?", (user_id, body.lessonId)).fetchone()
    if exists:
        db.close()
        return {"ok": True, "duplicate": True}
    db.execute("INSERT INTO lesson_completions (user_id, lesson_id, xp_earned) VALUES (?,?,?)", (user_id, body.lessonId, xp_reward))
    if body.correctAnswers > 0:
        db.execute("UPDATE progress SET correct_total = correct_total + ? WHERE user_id=?", (body.correctAnswers, user_id))
    add_xp(db, user_id, xp_reward)
    streak = update_streak(db, user_id)
    complete_daily_mission(db, user_id, "complete_lesson")
    unlock_achievement(db, user_id, "first_step")
    db.commit()
    db.close()
    return {"ok": True, "xp_earned": xp_reward, "streak": streak}


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
    user_level = int(prog["level"] if prog else 1)

    # Portfolio with total_value
    holdings = db.execute("SELECT ticker, shares, avg_price FROM portfolio WHERE user_id=? AND shares > 0", (user_id,)).fetchall()
    prices = get_daily_prices(user_id)
    total_value = balance
    for h in holdings:
        stock = STOCK_MAP.get(h["ticker"])
        current = float(prices.get(h["ticker"], stock["price"] if stock else 0))
        total_value += float(h["shares"]) * current
    total_pnl = total_value - START_BALANCE
    total_pnl_pct = round(total_pnl / START_BALANCE * 100, 2) if START_BALANCE > 0 else 0

    # Stats
    total_trades = db.execute("SELECT COUNT(*) AS cnt FROM transactions WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    lessons_done = db.execute("SELECT COUNT(*) AS cnt FROM lesson_completions WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    ach_count = db.execute("SELECT COUNT(*) AS cnt FROM user_achievements WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    completed_ids = {r["lesson_id"] for r in db.execute("SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user_id,)).fetchall()}

    # Next lesson — по слабым темам из онбординга
    mastery = ml_engine.compute_mastery_from_db(db, user_id)
    next_lesson_data = None

    # Онбординг → сортируем статические уроки по слабости
    onboarding_row = db.execute("SELECT topic_scores FROM onboarding_results WHERE user_id=?", (user_id,)).fetchone()
    topic_weakness = {}
    if onboarding_row and onboarding_row["topic_scores"]:
        try:
            ts = json.loads(onboarding_row["topic_scores"])
            for tid, d in ts.items():
                topic_weakness[tid] = d.get("score", d.get("mastery", 0.5)) if isinstance(d, dict) else 0.5
        except (json.JSONDecodeError, TypeError):
            pass

    # Собираем и сортируем статические уроки
    all_static = []
    for module in MODULES:
        for lesson in get_module_lessons(module["id"]):
            topic = lesson.get("skill_topic", "stocks")
            w = topic_weakness.get(topic, 0.5)
            m = mastery.get(topic, {}).get("mastery", w)
            all_static.append({**lesson, "_score": (w + m) / 2})
    all_static.sort(key=lambda x: x["_score"])

    for lesson in all_static:
        if lesson["id"] not in completed_ids:
            next_lesson_data = {
                "id": lesson["id"],
                "title": lesson["title"],
                "subtitle": lesson["subtitle"],
                "duration_min": lesson["duration_min"],
                "xp_reward": lesson["xp_reward"],
                "module_title": "Твоё обучение",
                "module_icon": "🧠",
                "generated": False,
            }
            break

    # Если все статические пройдены — AI-урок
    if not next_lesson_data:
        ai_stubs = get_lesson_stubs(mastery, completed_ids)
        # Найти первый непройденный
        stub = next((s for s in ai_stubs if not s["completed"]), None)
        if stub:
            next_lesson_data = {
                "id": stub["id"],
                "title": stub["title"],
                "subtitle": stub["subtitle"],
                "duration_min": stub["duration_min"],
                "xp_reward": stub["xp_reward"],
                "module_title": "Твоё обучение",
                "module_icon": "🧠",
                "generated": True,
                "weak_topic": stub["weak_topic"],
                "strong_topic": stub["strong_topic"],
            }

    # Daily missions
    today = date.today().isoformat()
    missions_raw = get_daily_missions(user_id)
    done_missions = {r["mission"] for r in db.execute("SELECT mission FROM daily_missions WHERE user_id=? AND date=? AND completed=1", (user_id, today)).fetchall()}
    daily_missions_out = [{"id": m["id"], "text": m["text"], "icon": m.get("icon", ""), "xp": m.get("xp", 25), "completed": m["id"] in done_missions} for m in missions_raw]

    # Module progress
    module_progress_out = []
    for module in MODULES:
        mod_lessons = get_module_lessons(module["id"])
        done = sum(1 for l in mod_lessons if l["id"] in completed_ids)
        total = len(mod_lessons)
        module_progress_out.append({"id": module["id"], "title": module["title"], "icon": module["icon"], "completed_count": done, "total_lessons": total, "progress_pct": round(done / total * 100) if total else 0})

    # Market event
    event_data = get_daily_event(user_id)
    event_out = None
    if event_data:
        seen = db.execute("SELECT id FROM market_events WHERE user_id=? AND event_id=?", (user_id, event_data.get("id", ""))).fetchone()
        impact_map = event_data.get("impact", {})
        affected = {}
        for h in holdings:
            stock = STOCK_MAP.get(h["ticker"])
            if stock and h["ticker"] in impact_map:
                impact_pct = round(impact_map[h["ticker"]] * 100, 2)
                value = float(h["shares"]) * float(prices.get(h["ticker"], stock["price"]))
                affected[h["ticker"]] = {"name": stock["name"], "impact_pct": impact_pct, "impact_amount": round(value * impact_pct / 100)}
        event_out = {"id": event_data.get("id"), "headline": event_data.get("headline", ""), "detail": event_data.get("detail", ""), "affected_holdings": affected, "seen": seen is not None}

    onboarding = db.execute("SELECT level_id FROM onboarding_results WHERE user_id=?", (user_id,)).fetchone()
    db.close()

    return {
        "level_info": get_level_for_xp(xp),
        "xp": xp,
        "streak": streak,
        "portfolio": {"balance": round(balance, 2), "total_value": round(total_value, 2), "total_pnl": round(total_pnl, 2), "total_pnl_pct": total_pnl_pct},
        "next_lesson": next_lesson_data,
        "daily_missions": daily_missions_out,
        "market_event": event_out,
        "module_progress": module_progress_out,
        "stats": {"trades_made": total_trades, "lessons_completed": lessons_done, "achievements": ach_count, "profit_pct": total_pnl_pct},
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
    mastery = ml_engine.compute_mastery_from_db(db, user_id)
    db.close()
    weak = [{"id": k, "mastery": v["mastery"], "trend": v["recent_trend"]} for k, v in mastery.items() if v["mastery"] < 0.5]
    strong = [{"id": k, "mastery": v["mastery"], "trend": v["recent_trend"]} for k, v in mastery.items() if v["mastery"] >= 0.7 and v["answers"] >= 3]
    weak.sort(key=lambda x: x["mastery"])
    strong.sort(key=lambda x: x["mastery"], reverse=True)
    return {"mastery": mastery, "weak_topics": weak, "strong_topics": strong}


@app.get("/adaptive/recommendation")
def adaptive_recommendation(userId: Optional[str] = Query(default=None), current_user: str = Depends(get_current_user)):
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    mastery = ml_engine.compute_mastery_from_db(db, user_id)
    priorities = ml_engine.get_topic_priorities(mastery)
    review = ml_engine.get_review_schedule(db, user_id, mastery)
    db.close()
    # Focus on highest priority topic
    focus = priorities[0] if priorities else None
    rec = {"type": "lesson", "topic_focus": focus["topic"] if focus else None, "reason": focus.get("reason", "") if focus else "Продолжай текущий модуль", "priority_list": priorities[:5]}
    return {"recommendation": rec, "review_due": review[:5]}


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
    # BKT mastery update
    mastery_all = ml_engine.compute_mastery_from_db(db, user_id)
    topic_data = mastery_all.get(body.topic, {"mastery": 0.0, "answers": 0})
    db.execute(
        "INSERT OR REPLACE INTO topic_mastery (user_id, topic, mastery, answers, updated_at) VALUES (?,?,?,?,datetime('now'))",
        (user_id, body.topic, float(topic_data["mastery"]), int(topic_data["answers"])),
    )
    db.commit()
    db.close()
    return {"ok": True, "mastery": topic_data["mastery"], "trend": topic_data.get("recent_trend", "unknown")}


@app.get("/adaptive/next-question")
def adaptive_next_question(
    topic: str = Query(...),
    userId: Optional[str] = Query(default=None),
    current_user: str = Depends(get_current_user),
):
    """ML-powered: подбирает вопрос по теме на основе mastery пользователя."""
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    mastery_all = ml_engine.compute_mastery_from_db(db, user_id)
    topic_mastery = mastery_all.get(topic, {"mastery": 0.1, "answers": 0})
    # ML engine выбирает оптимальную сложность
    optimal_diff = ml_engine.get_next_optimal_difficulty(topic, topic_mastery["mastery"])
    # Исключаем недавние вопросы
    recent = db.execute(
        "SELECT question_id FROM adaptive_answers WHERE user_id=? AND topic=? ORDER BY created_at DESC LIMIT 10",
        (user_id, topic),
    ).fetchall()
    db.close()
    exclude = [r["question_id"] for r in recent]
    q = get_adaptive_question(user_id, topic, optimal_diff, exclude)
    if not q:
        return {"ok": False, "error": "no_questions_available"}
    return {
        "ok": True,
        "question": {**q, "options": [{"text": o} for o in q["options"]]},
        "meta": {"mastery": topic_mastery["mastery"], "optimal_difficulty": optimal_diff, "trend": topic_mastery.get("recent_trend", "unknown")},
    }


@app.get("/adaptive/lesson-questions")
def adaptive_lesson_questions(
    topic: str = Query(...),
    count: int = Query(default=3),
    userId: Optional[str] = Query(default=None),
    current_user: str = Depends(get_current_user),
):
    """ML-powered: подбирает набор вопросов для урока, адаптированных по сложности."""
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    mastery_all = ml_engine.compute_mastery_from_db(db, user_id)
    topic_mastery = mastery_all.get(topic, {"mastery": 0.1})["mastery"]
    recent = db.execute(
        "SELECT question_id FROM adaptive_answers WHERE user_id=? AND topic=? ORDER BY created_at DESC LIMIT 20",
        (user_id, topic),
    ).fetchall()
    db.close()
    exclude = [r["question_id"] for r in recent]
    questions = get_questions_for_lesson(user_id, topic, topic_mastery, count, exclude)
    return {
        "ok": True,
        "questions": [{**q, "options": [{"text": o} for o in q["options"]]} for q in questions],
        "meta": {"topic": topic, "mastery": topic_mastery, "count": len(questions)},
    }


@app.get("/adaptive/generate-question")
async def adaptive_generate_question(
    topic: Optional[str] = Query(default=None),
    userId: Optional[str] = Query(default=None),
    current_user: str = Depends(get_current_user),
):
    """LLM-powered: генерирует уникальный вопрос через Claude API на основе mastery."""
    user_id = resolve_user_id(userId, current_user)
    db = get_db()
    mastery = ml_engine.compute_mastery_from_db(db, user_id)

    # Если тема не указана — выбираем автоматически по mastery
    if topic:
        topic_mastery = mastery.get(topic, {"mastery": 0.1, "answers": 0})["mastery"]
        if topic_mastery < 0.3:
            difficulty = 1
        elif topic_mastery < 0.6:
            difficulty = 2
        else:
            difficulty = 3
    else:
        topic, difficulty = select_topic_and_difficulty(mastery)

    recent = get_recent_questions(db, user_id, topic)
    db.close()

    question = await generate_question(topic, difficulty, recent)
    if not question:
        return {"ok": False, "error": "generation_failed", "fallback": True}

    topic_data = mastery.get(topic, {"mastery": 0.0, "answers": 0})
    return {
        "ok": True,
        "question": {**question, "options": [{"text": o} for o in question["options"]]},
        "meta": {
            "topic": topic,
            "topic_name": next((t["name"] for t in LEARNING_TOPICS if t["id"] == topic), topic),
            "mastery": topic_data["mastery"],
            "difficulty": difficulty,
            "generated": True,
        },
    }


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
