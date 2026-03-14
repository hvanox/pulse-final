"""
Pulse 2.0 — Backend API
Investment education platform with interactive lessons and portfolio simulator.
"""

from datetime import date, datetime, timedelta
import math

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from database import get_db, init_db
from stocks import (
    STOCKS, STOCK_MAP, get_stock, get_daily_prices, get_sparkline,
    get_daily_event, MARKET_EVENTS, LEVELS, get_level_for_xp,
    ACHIEVEMENTS, ACHIEVEMENT_MAP, get_daily_missions,
)
from lessons_v2 import MODULES, MODULE_MAP, LESSONS, LESSON_MAP, get_module_lessons
from cards import CARDS
from onboarding import (
    ONBOARDING_QUESTIONS, ONBOARDING_LEVELS, TOPICS as LEARNING_TOPICS,
    score_onboarding, compute_topic_mastery, get_weak_topics, get_strong_topics,
    recommend_next_content, get_topics_due_for_review,
)
import json

# Legacy ML selector
try:
    from ml.selector import select_next_card
except ImportError:
    import random
    def select_next_card(user_id, history, all_cards):
        return random.choice(all_cards)

# ML level predictor
try:
    from ml.features import extract_features
    from ml.model import LevelPredictor
    _level_predictor = LevelPredictor()
except ImportError:
    extract_features = None
    _level_predictor = None

# ML adaptive learning engine (Nazар's BKT + recommender + spaced repetition)
try:
    from ml.adaptive_engine import get_default_engine
    _adaptive_engine = get_default_engine()
except ImportError:
    _adaptive_engine = None


app = FastAPI(title="Pulse 2.0", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ═══════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════

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
    # Initialize progress with starter balance
    db.execute(
        "INSERT OR IGNORE INTO progress (user_id, streak, correct_total, xp, level, balance) VALUES (?,0,0,0,1,1000000)",
        (body.email,),
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


# ═══════════════════════════════════════════
# PROGRESS & GAMIFICATION
# ═══════════════════════════════════════════

@app.get("/progress")
def get_progress(userId: str):
    db = get_db()
    prog = db.execute("SELECT * FROM progress WHERE user_id=?", (userId,)).fetchone()
    db.close()
    if not prog:
        return {
            "streak": 0, "correct_total": 0, "last_active_date": None,
            "xp": 0, "level": 1, "balance": 1000000,
            "level_info": get_level_for_xp(0),
        }
    xp = prog["xp"] or 0
    return {
        **dict(prog),
        "level_info": get_level_for_xp(xp),
    }


def add_xp(db, user_id: str, amount: int):
    """Add XP and update level."""
    prog = db.execute("SELECT xp, level FROM progress WHERE user_id=?", (user_id,)).fetchone()
    if not prog:
        db.execute(
            "INSERT INTO progress (user_id, xp, level, balance) VALUES (?,?,1,1000000)",
            (user_id, amount),
        )
    else:
        new_xp = (prog["xp"] or 0) + amount
        level_info = get_level_for_xp(new_xp)
        new_level = level_info["current"]["level"]
        db.execute(
            "UPDATE progress SET xp=?, level=? WHERE user_id=?",
            (new_xp, new_level, user_id),
        )
    db.commit()


def update_streak(db, user_id: str):
    """Update streak on daily activity."""
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    prog = db.execute("SELECT * FROM progress WHERE user_id=?", (user_id,)).fetchone()
    if not prog:
        db.execute(
            "INSERT INTO progress (user_id, streak, last_active_date, xp, level, balance) VALUES (?,1,?,0,1,1000000)",
            (user_id, today),
        )
    else:
        last = prog["last_active_date"]
        streak = prog["streak"] or 0
        if last == today:
            return streak  # Already active today
        elif last == yesterday:
            streak += 1
        else:
            # Check for freeze
            freeze = db.execute(
                "SELECT id FROM streak_freezes WHERE user_id=? AND used_on IS NULL ORDER BY bought_at LIMIT 1",
                (user_id,),
            ).fetchone()
            if freeze:
                db.execute("UPDATE streak_freezes SET used_on=? WHERE id=?", (today, freeze["id"]))
                streak += 1
            else:
                streak = 1  # Reset
        db.execute(
            "UPDATE progress SET streak=?, last_active_date=? WHERE user_id=?",
            (streak, today, user_id),
        )
        # Streak achievements
        if streak >= 7:
            unlock_achievement(db, user_id, "streak_7")
        if streak >= 30:
            unlock_achievement(db, user_id, "streak_30")
    db.commit()
    return db.execute("SELECT streak FROM progress WHERE user_id=?", (user_id,)).fetchone()["streak"]


# ═══════════════════════════════════════════
# ACHIEVEMENTS
# ═══════════════════════════════════════════

def unlock_achievement(db, user_id: str, achievement_id: str):
    """Try to unlock an achievement. Returns True if newly unlocked."""
    existing = db.execute(
        "SELECT id FROM user_achievements WHERE user_id=? AND achievement=?",
        (user_id, achievement_id),
    ).fetchone()
    if existing:
        return False
    db.execute(
        "INSERT INTO user_achievements (user_id, achievement) VALUES (?,?)",
        (user_id, achievement_id),
    )
    # Award XP for achievement
    ach = ACHIEVEMENT_MAP.get(achievement_id)
    if ach:
        add_xp(db, user_id, ach["xp_reward"])
    return True


@app.get("/achievements")
def get_achievements(userId: str):
    db = get_db()
    unlocked = db.execute(
        "SELECT achievement, unlocked_at FROM user_achievements WHERE user_id=?",
        (userId,),
    ).fetchall()
    db.close()
    unlocked_map = {r["achievement"]: r["unlocked_at"] for r in unlocked}
    result = []
    for ach in ACHIEVEMENTS:
        result.append({
            **ach,
            "unlocked": ach["id"] in unlocked_map,
            "unlocked_at": unlocked_map.get(ach["id"]),
        })
    return result


# ═══════════════════════════════════════════
# PORTFOLIO & TRADING
# ═══════════════════════════════════════════

@app.get("/portfolio")
def get_portfolio(userId: str):
    db = get_db()
    prog = db.execute("SELECT balance FROM progress WHERE user_id=?", (userId,)).fetchone()
    balance = prog["balance"] if prog else 1000000

    holdings = db.execute(
        "SELECT ticker, shares, avg_price FROM portfolio WHERE user_id=? AND shares > 0",
        (userId,),
    ).fetchall()

    prices = get_daily_prices(userId)
    portfolio_items = []
    total_value = balance

    for h in holdings:
        stock = STOCK_MAP.get(h["ticker"])
        current_price = prices.get(h["ticker"], stock["price"] if stock else 0)
        value = h["shares"] * current_price
        cost = h["shares"] * h["avg_price"]
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0
        total_value += value
        portfolio_items.append({
            "ticker": h["ticker"],
            "name": stock["name"] if stock else h["ticker"],
            "name_ru": stock["name_ru"] if stock else h["ticker"],
            "shares": h["shares"],
            "avg_price": h["avg_price"],
            "current_price": current_price,
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "logo_emoji": stock["logo_emoji"] if stock else "📊",
            "color": stock["color"] if stock else "#888",
            "sector": stock["sector"] if stock else "",
        })

    # Sort by value descending
    portfolio_items.sort(key=lambda x: x["value"], reverse=True)

    # Sparkline for total portfolio (simplified: use weighted avg of holdings)
    sparkline = []
    for d in range(30, -1, -1):
        day_prices = get_daily_prices(userId, d)
        day_total = balance
        for h in holdings:
            p = day_prices.get(h["ticker"], h["avg_price"])
            day_total += h["shares"] * p
        sparkline.append(round(day_total, 2))

    # Calculate allocation
    allocations = []
    for item in portfolio_items:
        allocations.append({
            "ticker": item["ticker"],
            "name": item["name"],
            "pct": round(item["value"] / total_value * 100, 1) if total_value > 0 else 0,
            "color": item["color"],
        })
    cash_pct = round(balance / total_value * 100, 1) if total_value > 0 else 100
    allocations.append({"ticker": "CASH", "name": "Кэш", "pct": cash_pct, "color": "#e0e0e0"})

    db.close()
    return {
        "balance": balance,
        "total_value": round(total_value, 2),
        "total_pnl": round(total_value - 1000000, 2),
        "total_pnl_pct": round((total_value - 1000000) / 1000000 * 100, 2),
        "holdings": portfolio_items,
        "allocations": allocations,
        "sparkline": sparkline,
    }


class TradeBody(BaseModel):
    userId: str
    ticker: str
    shares: float
    action: str  # "buy" or "sell"


@app.post("/trade")
def trade(body: TradeBody):
    stock = get_stock(body.ticker)
    if not stock:
        return {"ok": False, "error": "Акция не найдена"}

    db = get_db()
    prices = get_daily_prices(body.userId)
    price = prices.get(body.ticker, stock["price"])
    total = price * body.shares

    prog = db.execute("SELECT balance FROM progress WHERE user_id=?", (body.userId,)).fetchone()
    balance = prog["balance"] if prog else 1000000

    if body.action == "buy":
        if total > balance:
            db.close()
            return {"ok": False, "error": "Недостаточно средств"}

        # Update balance
        db.execute("UPDATE progress SET balance=? WHERE user_id=?", (balance - total, body.userId))

        # Update portfolio
        existing = db.execute(
            "SELECT shares, avg_price FROM portfolio WHERE user_id=? AND ticker=?",
            (body.userId, body.ticker),
        ).fetchone()
        if existing:
            new_shares = existing["shares"] + body.shares
            new_avg = (existing["shares"] * existing["avg_price"] + body.shares * price) / new_shares
            db.execute(
                "UPDATE portfolio SET shares=?, avg_price=? WHERE user_id=? AND ticker=?",
                (new_shares, new_avg, body.userId, body.ticker),
            )
        else:
            db.execute(
                "INSERT INTO portfolio (user_id, ticker, shares, avg_price) VALUES (?,?,?,?)",
                (body.userId, body.ticker, body.shares, price),
            )

        # Record transaction
        db.execute(
            "INSERT INTO transactions (user_id, ticker, action, shares, price, total) VALUES (?,?,?,?,?,?)",
            (body.userId, body.ticker, "buy", body.shares, price, total),
        )

        # Diary entry
        db.execute(
            "INSERT INTO diary (user_id, entry_type, title, detail, ticker) VALUES (?,?,?,?,?)",
            (body.userId, "trade", f"Купил {body.shares} акций {stock['name']}",
             f"По цене {price:,.0f} ₽ за акцию. Итого: {total:,.0f} ₽", body.ticker),
        )

        # Achievement: first buy
        unlock_achievement(db, body.userId, "first_buy")

        # Check diversifier
        holdings_count = db.execute(
            "SELECT COUNT(DISTINCT ticker) as cnt FROM portfolio WHERE user_id=? AND shares > 0",
            (body.userId,),
        ).fetchone()["cnt"]
        if holdings_count >= 5:
            unlock_achievement(db, body.userId, "diversifier")

        # Check global investor (has both RU and foreign)
        tickers = [r["ticker"] for r in db.execute(
            "SELECT DISTINCT ticker FROM portfolio WHERE user_id=? AND shares > 0", (body.userId,)
        ).fetchall()]
        ru_tickers = {"SBER", "GAZP", "YNDX", "LKOH", "TCSG"}
        has_ru = bool(set(tickers) & ru_tickers)
        has_foreign = bool(set(tickers) - ru_tickers)
        if has_ru and has_foreign:
            unlock_achievement(db, body.userId, "global_investor")

        # Daily mission: make_trade
        complete_daily_mission(db, body.userId, "make_trade")

        # Add XP for trading
        add_xp(db, body.userId, 10)

        db.commit()
        db.close()
        return {"ok": True, "action": "buy", "ticker": body.ticker, "shares": body.shares, "price": price, "total": total}

    elif body.action == "sell":
        existing = db.execute(
            "SELECT shares, avg_price FROM portfolio WHERE user_id=? AND ticker=?",
            (body.userId, body.ticker),
        ).fetchone()
        if not existing or existing["shares"] < body.shares:
            db.close()
            return {"ok": False, "error": "Недостаточно акций"}

        new_shares = existing["shares"] - body.shares
        db.execute("UPDATE progress SET balance=? WHERE user_id=?", (balance + total, body.userId))
        db.execute(
            "UPDATE portfolio SET shares=? WHERE user_id=? AND ticker=?",
            (new_shares, body.userId, body.ticker),
        )
        db.execute(
            "INSERT INTO transactions (user_id, ticker, action, shares, price, total) VALUES (?,?,?,?,?,?)",
            (body.userId, body.ticker, "sell", body.shares, price, total),
        )

        pnl = (price - existing["avg_price"]) * body.shares
        db.execute(
            "INSERT INTO diary (user_id, entry_type, title, detail, ticker) VALUES (?,?,?,?,?)",
            (body.userId, "trade", f"Продал {body.shares} акций {stock['name']}",
             f"По цене {price:,.0f} ₽. P&L: {pnl:+,.0f} ₽", body.ticker),
        )

        complete_daily_mission(db, body.userId, "make_trade")
        add_xp(db, body.userId, 10)

        db.commit()
        db.close()
        return {"ok": True, "action": "sell", "ticker": body.ticker, "shares": body.shares, "price": price, "total": total, "pnl": round(pnl, 2)}

    return {"ok": False, "error": "Неизвестное действие"}


# ═══════════════════════════════════════════
# MARKET / STOCKS
# ═══════════════════════════════════════════

@app.get("/stocks")
def get_stocks(userId: str):
    prices = get_daily_prices(userId)
    result = []
    for stock in STOCKS:
        current_price = prices.get(stock["ticker"], stock["price"])
        change_pct = round((current_price - stock["price"]) / stock["price"] * 100, 2)
        sparkline = get_sparkline(userId, stock["ticker"])
        result.append({
            **stock,
            "current_price": current_price,
            "change_pct": change_pct,
            "sparkline": sparkline,
        })
    return result


@app.get("/stock/{ticker}")
def get_stock_detail(ticker: str, userId: str):
    stock = get_stock(ticker)
    if not stock:
        return {"error": "Stock not found"}
    prices = get_daily_prices(userId)
    current_price = prices.get(ticker, stock["price"])
    sparkline = get_sparkline(userId, ticker, 60)
    return {
        **stock,
        "current_price": current_price,
        "sparkline": sparkline,
    }


@app.get("/market-event")
def get_market_event(userId: str):
    """Get today's market event for user."""
    event = get_daily_event(userId)
    if not event:
        return {"event": None}

    db = get_db()
    existing = db.execute(
        "SELECT seen, action FROM market_events WHERE user_id=? AND event_id=?",
        (userId, event["id"]),
    ).fetchone()
    db.close()

    return {
        "event": {
            **event,
            "seen": bool(existing and existing["seen"]) if existing else False,
            "user_action": existing["action"] if existing else None,
        }
    }


class EventActionBody(BaseModel):
    userId: str
    eventId: str
    action: str  # "hold", "sell", "details"


@app.post("/market-event/action")
def market_event_action(body: EventActionBody):
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO market_events (user_id, event_id, action, seen) VALUES (?,?,?,1)",
        (body.userId, body.eventId, body.action),
    )
    complete_daily_mission(db, body.userId, "read_event")
    add_xp(db, body.userId, 10)
    db.commit()
    db.close()
    return {"ok": True}


# ═══════════════════════════════════════════
# LESSONS V2
# ═══════════════════════════════════════════

@app.get("/v2/modules")
def get_modules(userId: str):
    db = get_db()
    prog = db.execute("SELECT level, xp FROM progress WHERE user_id=?", (userId,)).fetchone()
    user_level = prog["level"] if prog else 1

    completions = db.execute(
        "SELECT lesson_id FROM lesson_completions WHERE user_id=?", (userId,)
    ).fetchall()
    completed_lessons = {r["lesson_id"] for r in completions}
    db.close()

    result = []
    for module in MODULES:
        lessons = get_module_lessons(module["id"])
        completed_count = sum(1 for l in lessons if l["id"] in completed_lessons)
        total = len(lessons)
        locked = user_level < module["required_level"]
        result.append({
            **module,
            "completed_count": completed_count,
            "total_lessons": total,
            "progress_pct": round(completed_count / total * 100) if total > 0 else 0,
            "locked": locked,
        })
    return result


@app.get("/v2/lessons")
def get_lessons_v2(userId: str, moduleId: str):
    db = get_db()
    completions = db.execute(
        "SELECT lesson_id FROM lesson_completions WHERE user_id=?", (userId,)
    ).fetchall()
    completed_lessons = {r["lesson_id"] for r in completions}
    db.close()

    lessons = get_module_lessons(moduleId)
    result = []
    for i, lesson in enumerate(lessons):
        # Lock logic: first lesson always unlocked, others need previous completed
        locked = False
        if i > 0:
            prev_lesson = lessons[i - 1]
            if prev_lesson["id"] not in completed_lessons:
                locked = True

        result.append({
            "id": lesson["id"],
            "title": lesson["title"],
            "subtitle": lesson["subtitle"],
            "duration_min": lesson["duration_min"],
            "xp_reward": lesson["xp_reward"],
            "skill": lesson["skill"],
            "order": lesson["order"],
            "completed": lesson["id"] in completed_lessons,
            "locked": locked,
            "screen_count": len(lesson["screens"]),
        })
    return result


@app.get("/v2/lesson/{lessonId}")
def get_lesson_detail(lessonId: str, userId: str):
    from lessons_v2 import get_lesson
    lesson = get_lesson(lessonId)
    if not lesson:
        return {"error": "Lesson not found"}

    db = get_db()
    completed = db.execute(
        "SELECT id FROM lesson_completions WHERE user_id=? AND lesson_id=?",
        (userId, lessonId),
    ).fetchone()
    db.close()

    return {
        **lesson,
        "completed": completed is not None,
    }


class CompleteLessonBody(BaseModel):
    userId: str
    lessonId: str
    correctAnswers: int = 0
    totalQuestions: int = 0


@app.post("/v2/complete-lesson")
def complete_lesson_v2(body: CompleteLessonBody):
    lesson = LESSON_MAP.get(body.lessonId)
    if not lesson:
        return {"ok": False, "error": "Lesson not found"}

    db = get_db()
    existing = db.execute(
        "SELECT id FROM lesson_completions WHERE user_id=? AND lesson_id=?",
        (body.userId, body.lessonId),
    ).fetchone()
    if existing:
        db.close()
        return {"ok": True, "duplicate": True}

    xp = lesson["xp_reward"]
    db.execute(
        "INSERT INTO lesson_completions (user_id, lesson_id, xp_earned) VALUES (?,?,?)",
        (body.userId, body.lessonId, xp),
    )

    # Add XP
    add_xp(db, body.userId, xp)

    # Update streak
    streak = update_streak(db, body.userId)

    # Update correct_total
    if body.correctAnswers > 0:
        db.execute(
            "UPDATE progress SET correct_total = correct_total + ? WHERE user_id=?",
            (body.correctAnswers, body.userId),
        )

    # Achievement: first_step
    total_lessons = db.execute(
        "SELECT COUNT(*) as cnt FROM lesson_completions WHERE user_id=?", (body.userId,)
    ).fetchone()["cnt"]
    if total_lessons == 1:
        unlock_achievement(db, body.userId, "first_step")
    if total_lessons >= 10:
        unlock_achievement(db, body.userId, "diligent_student")

    # Check module completion
    module = MODULE_MAP.get(lesson["module_id"])
    if module:
        module_lessons = get_module_lessons(module["id"])
        completed_in_module = db.execute(
            "SELECT COUNT(*) as cnt FROM lesson_completions WHERE user_id=? AND lesson_id LIKE ?",
            (body.userId, f"{module['id'].replace('m', '')}%"),
        ).fetchone()["cnt"]
        # More reliable: check all lessons
        completed_ids = {r["lesson_id"] for r in db.execute(
            "SELECT lesson_id FROM lesson_completions WHERE user_id=?", (body.userId,)
        ).fetchall()}
        all_module_done = all(l["id"] in completed_ids for l in module_lessons)
        if all_module_done:
            unlock_achievement(db, body.userId, "encyclopedist")
            if module["id"] == "m1":
                unlock_achievement(db, body.userId, "master_basics")

        # Check if entire course complete
        all_done = all(l["id"] in completed_ids for l in LESSONS)
        if all_done:
            unlock_achievement(db, body.userId, "course_complete")

    # Daily mission
    complete_daily_mission(db, body.userId, "complete_lesson")

    # Diary
    db.execute(
        "INSERT INTO diary (user_id, entry_type, title, detail) VALUES (?,?,?,?)",
        (body.userId, "lesson", f"Пройден урок: {lesson['title']}",
         f"+{xp} XP • Навык: {lesson['skill']}"),
    )

    db.commit()
    db.close()
    return {
        "ok": True,
        "xp_earned": xp,
        "streak": streak,
        "skill": lesson["skill"],
    }


# ═══════════════════════════════════════════
# DAILY MISSIONS
# ═══════════════════════════════════════════

@app.get("/daily-missions")
def get_daily_missions_endpoint(userId: str):
    today = str(date.today())
    missions = get_daily_missions(userId)

    db = get_db()
    completed = db.execute(
        "SELECT mission FROM daily_missions WHERE user_id=? AND date=? AND completed=1",
        (userId, today),
    ).fetchall()
    completed_ids = {r["mission"] for r in completed}
    db.close()

    result = []
    for m in missions:
        result.append({
            **m,
            "completed": m["id"] in completed_ids,
        })
    all_done = all(m["id"] in completed_ids for m in missions)
    return {
        "missions": result,
        "all_completed": all_done,
        "bonus_xp": 50 if all_done else 0,
    }


def complete_daily_mission(db, user_id: str, mission_id: str):
    """Mark a daily mission as completed."""
    today = str(date.today())
    missions = get_daily_missions(user_id)
    if any(m["id"] == mission_id for m in missions):
        db.execute(
            "INSERT OR REPLACE INTO daily_missions (user_id, mission, completed, date) VALUES (?,?,1,?)",
            (user_id, mission_id, today),
        )
        # Check if all completed for bonus
        completed = db.execute(
            "SELECT COUNT(*) as cnt FROM daily_missions WHERE user_id=? AND date=? AND completed=1",
            (user_id, today),
        ).fetchone()["cnt"]
        if completed >= len(missions):
            add_xp(db, user_id, 50)  # Bonus for all missions


# ═══════════════════════════════════════════
# DIARY
# ═══════════════════════════════════════════

@app.get("/diary")
def get_diary(userId: str, limit: int = 20):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM diary WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (userId, limit),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════
# TRANSACTIONS HISTORY
# ═══════════════════════════════════════════

@app.get("/transactions")
def get_transactions(userId: str, limit: int = 30):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (userId, limit),
    ).fetchall()
    db.close()
    result = []
    for r in rows:
        stock = STOCK_MAP.get(r["ticker"])
        result.append({
            **dict(r),
            "name": stock["name"] if stock else r["ticker"],
            "logo_emoji": stock["logo_emoji"] if stock else "📊",
        })
    return result


# ═══════════════════════════════════════════
# DASHBOARD / HOME
# ═══════════════════════════════════════════

@app.get("/dashboard")
def get_dashboard(userId: str):
    """Main screen data — combines portfolio, next lesson, daily missions, event."""
    db = get_db()

    # Progress
    prog = db.execute("SELECT * FROM progress WHERE user_id=?", (userId,)).fetchone()
    xp = prog["xp"] if prog else 0
    level_info = get_level_for_xp(xp)
    streak = prog["streak"] if prog else 0
    balance = prog["balance"] if prog else 1000000

    # Portfolio summary
    holdings = db.execute(
        "SELECT ticker, shares, avg_price FROM portfolio WHERE user_id=? AND shares > 0",
        (userId,),
    ).fetchall()
    prices = get_daily_prices(userId)
    total_value = balance
    for h in holdings:
        stock = STOCK_MAP.get(h["ticker"])
        price = prices.get(h["ticker"], stock["price"] if stock else 0)
        total_value += h["shares"] * price

    # Completed lessons
    completions = db.execute(
        "SELECT lesson_id FROM lesson_completions WHERE user_id=?", (userId,)
    ).fetchall()
    completed_lessons = {r["lesson_id"] for r in completions}

    # Next lesson
    next_lesson = None
    for lesson in LESSONS:
        if lesson["id"] not in completed_lessons:
            module = MODULE_MAP.get(lesson["module_id"])
            user_level = prog["level"] if prog else 1
            if module and user_level >= module["required_level"]:
                # Check if previous lesson in module is completed
                module_lessons = get_module_lessons(module["id"])
                idx = next((i for i, l in enumerate(module_lessons) if l["id"] == lesson["id"]), 0)
                if idx == 0 or module_lessons[idx - 1]["id"] in completed_lessons:
                    next_lesson = {
                        "id": lesson["id"],
                        "title": lesson["title"],
                        "subtitle": lesson["subtitle"],
                        "module_title": module["title"],
                        "module_icon": module["icon"],
                        "duration_min": lesson["duration_min"],
                        "xp_reward": lesson["xp_reward"],
                    }
                    break

    # Daily missions
    today = str(date.today())
    missions = get_daily_missions(userId)
    mission_completions = db.execute(
        "SELECT mission FROM daily_missions WHERE user_id=? AND date=? AND completed=1",
        (userId, today),
    ).fetchall()
    mission_done_ids = {r["mission"] for r in mission_completions}

    # Market event
    event = get_daily_event(userId)
    event_data = None
    if event:
        evt_record = db.execute(
            "SELECT seen FROM market_events WHERE user_id=? AND event_id=?",
            (userId, event["id"]),
        ).fetchone()
        # Check if user has relevant holdings
        user_tickers = {h["ticker"] for h in holdings}
        affected = {}
        for ticker, impact in event["impact"].items():
            if ticker in user_tickers:
                holding = next((h for h in holdings if h["ticker"] == ticker), None)
                if holding:
                    stock = STOCK_MAP.get(ticker)
                    current_price = prices.get(ticker, stock["price"])
                    change = current_price * impact
                    affected[ticker] = {
                        "name": stock["name"],
                        "impact_pct": round(impact * 100, 1),
                        "impact_amount": round(change * holding["shares"], 0),
                    }
        event_data = {
            "id": event["id"],
            "headline": event["headline"],
            "detail": event["detail"],
            "category": event["category"],
            "seen": bool(evt_record),
            "affected_holdings": affected,
        }

    # Module progress
    module_progress = []
    user_level = prog["level"] if prog else 1
    for module in MODULES:
        m_lessons = get_module_lessons(module["id"])
        done = sum(1 for l in m_lessons if l["id"] in completed_lessons)
        total = len(m_lessons)
        module_progress.append({
            "id": module["id"],
            "title": module["title"],
            "icon": module["icon"],
            "completed": done,
            "total": total,
            "progress_pct": round(done / total * 100) if total > 0 else 0,
            "locked": user_level < module["required_level"],
        })

    # Stats
    total_trades = db.execute(
        "SELECT COUNT(*) as cnt FROM transactions WHERE user_id=?", (userId,)
    ).fetchone()["cnt"]

    # Achievements count
    ach_count = db.execute(
        "SELECT COUNT(*) as cnt FROM user_achievements WHERE user_id=?", (userId,)
    ).fetchone()["cnt"]

    # Onboarding status
    onboarding = db.execute(
        "SELECT level_id FROM onboarding_results WHERE user_id=?", (userId,)
    ).fetchone()
    onboarding_completed = onboarding is not None

    db.close()

    return {
        "portfolio": {
            "total_value": round(total_value, 2),
            "total_pnl": round(total_value - 1000000, 2),
            "total_pnl_pct": round((total_value - 1000000) / 1000000 * 100, 2),
            "balance": balance,
        },
        "level_info": level_info,
        "streak": streak,
        "xp": xp,
        "next_lesson": next_lesson,
        "daily_missions": [
            {**m, "completed": m["id"] in mission_done_ids} for m in missions
        ],
        "market_event": event_data,
        "module_progress": module_progress,
        "stats": {
            "lessons_completed": len(completed_lessons),
            "trades_made": total_trades,
            "portfolio_return_pct": round((total_value - 1000000) / 1000000 * 100, 1),
            "achievements": ach_count,
        },
        "onboarding_completed": onboarding_completed,
    }


# ═══════════════════════════════════════════
# PORTFOLIO CHECK (daily mission)
# ═══════════════════════════════════════════

@app.post("/check-portfolio")
def check_portfolio(userId: str):
    db = get_db()
    complete_daily_mission(db, userId, "check_portfolio")
    update_streak(db, userId)
    db.commit()
    db.close()
    return {"ok": True}


# ═══════════════════════════════════════════
# STREAK FREEZE
# ═══════════════════════════════════════════

class FreezeBody(BaseModel):
    userId: str


@app.post("/buy-freeze")
def buy_freeze(body: FreezeBody):
    db = get_db()
    prog = db.execute("SELECT xp FROM progress WHERE user_id=?", (body.userId,)).fetchone()
    if not prog or (prog["xp"] or 0) < 200:
        db.close()
        return {"ok": False, "error": "Недостаточно XP (нужно 200)"}
    db.execute("UPDATE progress SET xp = xp - 200 WHERE user_id=?", (body.userId,))
    db.execute("INSERT INTO streak_freezes (user_id) VALUES (?)", (body.userId,))
    db.commit()
    db.close()
    return {"ok": True}


# ═══════════════════════════════════════════
# LEVELS INFO
# ═══════════════════════════════════════════

@app.get("/levels")
def get_levels():
    return LEVELS


# ═══════════════════════════════════════════
# ONBOARDING TEST
# ═══════════════════════════════════════════

@app.get("/onboarding/questions")
def get_onboarding_questions():
    """Return all onboarding questions for the test."""
    # Return questions without correct answers (frontend handles locally)
    questions = []
    for q in ONBOARDING_QUESTIONS:
        questions.append({
            "id": q["id"],
            "topic": q["topic"],
            "difficulty": q["difficulty"],
            "type": q["type"],
            "scenario": q["scenario"],
            "question": q["question"],
            "options": [{"text": o["text"]} for o in q["options"]],
        })
    return {"questions": questions, "total": len(questions)}


@app.get("/onboarding/status")
def get_onboarding_status(userId: str):
    """Check if user has completed onboarding."""
    db = get_db()
    result = db.execute(
        "SELECT level_id, score, start_module, start_lesson, completed_at FROM onboarding_results WHERE user_id=?",
        (userId,),
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
    }


class OnboardingSubmitBody(BaseModel):
    userId: str
    answers: list  # [{"question_id": str, "selected_index": int, "time_ms": int}]


@app.post("/onboarding/submit")
def submit_onboarding(body: OnboardingSubmitBody):
    """Submit onboarding test answers and get results."""
    result = score_onboarding(body.answers)

    db = get_db()

    # Save results
    db.execute(
        """INSERT OR REPLACE INTO onboarding_results
           (user_id, level_id, score, topic_scores, answers_json, start_module, start_lesson)
           VALUES (?,?,?,?,?,?,?)""",
        (
            body.userId,
            result["level"]["id"],
            result["score"],
            json.dumps(result["topic_scores"], ensure_ascii=False),
            json.dumps(body.answers, ensure_ascii=False),
            result["recommended_start"]["module"],
            result["recommended_start"]["lesson"],
        ),
    )

    # Save adaptive answers from onboarding
    for detail in result["details"]:
        db.execute(
            "INSERT INTO adaptive_answers (user_id, topic, question_id, is_correct, time_ms, source) VALUES (?,?,?,?,?,?)",
            (body.userId, detail["topic"], detail["question_id"], int(detail["is_correct"]), detail.get("time_ms", 0), "onboarding"),
        )

    # Update investor_type in progress
    db.execute(
        "UPDATE progress SET investor_type=? WHERE user_id=?",
        (result["level"]["id"], body.userId),
    )

    # Award XP bonus for completing onboarding
    add_xp(db, body.userId, result["xp_bonus"])

    # Auto-complete Module 1 lessons if advanced level
    if result["level"]["id"] == "advanced":
        for lid in ["1.1", "1.2", "1.3", "1.4"]:
            db.execute(
                "INSERT OR IGNORE INTO lesson_completions (user_id, lesson_id, xp_earned) VALUES (?,?,0)",
                (body.userId, lid),
            )
    elif result["level"]["id"] == "basic":
        for lid in ["1.1", "1.2"]:
            db.execute(
                "INSERT OR IGNORE INTO lesson_completions (user_id, lesson_id, xp_earned) VALUES (?,?,0)",
                (body.userId, lid),
            )

    db.commit()
    db.close()

    return {
        "ok": True,
        "level": result["level"],
        "score": result["score"],
        "score_pct": result["score_pct"],
        "total_correct": result["total_correct"],
        "total_questions": result["total_questions"],
        "strong_topics": result["strong_topics"],
        "weak_topics": result["weak_topics"],
        "learning_plan": result["learning_plan"],
        "recommended_start": result["recommended_start"],
        "xp_bonus": result["xp_bonus"],
        "topic_scores": result["topic_scores"],
    }


@app.get("/onboarding/result")
def get_onboarding_result(userId: str):
    """Get saved onboarding result for results screen."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM onboarding_results WHERE user_id=?", (userId,)
    ).fetchone()
    db.close()
    if not row:
        return {"ok": False}

    level = next((l for l in ONBOARDING_LEVELS if l["id"] == row["level_id"]), ONBOARDING_LEVELS[0])
    topic_scores = {}
    try:
        topic_scores = json.loads(row["topic_scores"]) if row["topic_scores"] else {}
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "ok": True,
        "level": level,
        "score": row["score"],
        "topic_scores": topic_scores,
        "start_module": row["start_module"],
        "start_lesson": row["start_lesson"],
    }


# ═══════════════════════════════════════════
# ADAPTIVE LEARNING
# ═══════════════════════════════════════════

@app.get("/adaptive/mastery")
def get_mastery(userId: str):
    """Get per-topic mastery scores (BKT-based if ML available, else rule-based)."""
    db = get_db()
    mastery = compute_topic_mastery(db, userId)

    result = {
        "mastery": mastery,
        "weak_topics": get_weak_topics(mastery),
        "strong_topics": get_strong_topics(mastery),
        "method": "rule-based",
    }

    if _adaptive_engine is not None:
        bkt_mastery = _adaptive_engine.compute_mastery_from_db(db, userId)
        result["bkt_mastery"] = bkt_mastery
        result["method"] = "bkt+rule-based"

    db.close()
    return result


@app.get("/adaptive/recommendation")
def get_recommendation(userId: str):
    """Get adaptive lesson recommendation (ML-enhanced if available)."""
    db = get_db()
    mastery = compute_topic_mastery(db, userId)
    rec = recommend_next_content(db, userId, mastery)
    due = get_topics_due_for_review(db, userId, mastery)

    result = {
        "recommendation": rec,
        "review_due": due[:3],
        "method": "rule-based",
    }

    if _adaptive_engine is not None:
        from lessons_v2 import LESSONS
        bkt_mastery = _adaptive_engine.compute_mastery_from_db(db, userId)
        # Build content list from lessons for ML recommender
        content_pool = [
            {"id": l["id"], "topic": l.get("topic", ""), "difficulty": l.get("difficulty", 1), "title": l.get("title", "")}
            for l in LESSONS
            if l.get("topic") and l.get("difficulty")
        ]
        if content_pool:
            ml_recs = _adaptive_engine.recommend_content(bkt_mastery, content_pool, top_k=3)
            result["ml_recommendations"] = ml_recs
        review_schedule = _adaptive_engine.get_review_schedule(db, userId, bkt_mastery)
        result["review_schedule"] = review_schedule[:3]
        result["topic_priorities"] = _adaptive_engine.get_topic_priorities(bkt_mastery)[:3]
        result["method"] = "ml+rule-based"

    db.close()
    return result


class AdaptiveAnswerBody(BaseModel):
    userId: str
    topic: str
    questionId: str = ""
    isCorrect: bool
    timeMs: int = 0
    source: str = "lesson"


@app.post("/adaptive/answer")
def record_adaptive_answer(body: AdaptiveAnswerBody):
    """Record an answer for adaptive tracking."""
    db = get_db()
    db.execute(
        "INSERT INTO adaptive_answers (user_id, topic, question_id, is_correct, time_ms, source) VALUES (?,?,?,?,?,?)",
        (body.userId, body.topic, body.questionId, int(body.isCorrect), body.timeMs, body.source),
    )
    db.commit()

    # Update cached mastery
    mastery = compute_topic_mastery(db, body.userId)
    topic_data = mastery.get(body.topic, {})
    db.execute(
        "INSERT OR REPLACE INTO topic_mastery (user_id, topic, mastery, answers) VALUES (?,?,?,?)",
        (body.userId, body.topic, topic_data.get("mastery", 0), topic_data.get("answers", 0)),
    )
    db.commit()
    db.close()

    return {"ok": True, "mastery": topic_data.get("mastery", 0)}


# ═══════════════════════════════════════════
# LEGACY ENDPOINTS (backward compatibility)
# ═══════════════════════════════════════════

@app.get("/experience")
def get_experience(userId: str):
    db = get_db()
    today = str(date.today())
    rows = db.execute(
        "SELECT card_id, is_correct, difficulty FROM interactions WHERE user_id=? AND date(created_at)=?",
        (userId, today),
    ).fetchall()
    history = [{"card_id": r["card_id"], "is_correct": bool(r["is_correct"]), "difficulty": r["difficulty"]} for r in rows]
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
        "INSERT INTO interactions (user_id, card_id, answer_index, is_correct, difficulty) VALUES (?,?,?,?,?)",
        (body.userId, body.cardId, body.answer_index, int(is_correct), card["difficulty"] if card else 1),
    )
    if is_correct:
        db.execute(
            "UPDATE progress SET correct_total = correct_total + 1 WHERE user_id=?",
            (body.userId,),
        )
        add_xp(db, body.userId, 15)
    db.commit()
    db.close()
    return {"is_correct": is_correct, "correct_index": card["correct_index"] if card else None}


@app.get("/audit")
def get_audit(userId: str):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM interactions WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        (userId,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════
# ML
# ═══════════════════════════════════════════

@app.get("/ml/features/{userId}")
def get_ml_features(userId: str):
    """Return extracted ML feature vector for a user."""
    if extract_features is None:
        return {"error": "ML module not available"}
    db = get_db()
    features = extract_features(db, userId)
    db.close()
    return features


class PredictLevelBody(BaseModel):
    userId: str


@app.post("/ml/predict-level")
def predict_level(body: PredictLevelBody):
    """
    Predict user level using the ML model.
    Falls back to rule-based logic if no trained model exists.
    """
    if _level_predictor is None or extract_features is None:
        return {"error": "ML module not available"}
    db = get_db()
    features = extract_features(db, body.userId)
    db.close()
    result = _level_predictor.predict(features)
    return result
