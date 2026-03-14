import json
import os
import sqlite3

from onboarding import SEED_ONBOARDING_QUESTIONS

DB_PATH = os.getenv("DB_PATH", "pulse_fresh.db")
START_BALANCE = int(os.getenv("START_BALANCE", "1000000"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def seed_onboarding_questions(conn: sqlite3.Connection):
    existing = conn.execute("SELECT COUNT(*) AS cnt FROM onboarding_questions").fetchone()["cnt"]
    if existing > 0:
        return

    for idx, q in enumerate(SEED_ONBOARDING_QUESTIONS, start=1):
        conn.execute(
            """
            INSERT INTO onboarding_questions
            (question_id, topic, difficulty, qtype, scenario, question, options_json, correct_index, weight, order_no, is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?,1)
            """,
            (
                q["id"],
                q["topic"],
                q["difficulty"],
                q["type"],
                q["scenario"],
                q["question"],
                json.dumps(q["options"], ensure_ascii=False),
                q["correct_index"],
                q["weight"],
                idx,
            ),
        )


def init_db():
    conn = get_db()
    conn.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS progress (
            user_id TEXT PRIMARY KEY,
            streak INTEGER DEFAULT 0,
            correct_total INTEGER DEFAULT 0,
            last_active_date TEXT,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            balance INTEGER DEFAULT {START_BALANCE},
            investor_type TEXT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            card_id INTEGER NOT NULL,
            answer_index INTEGER NOT NULL,
            is_correct INTEGER NOT NULL,
            difficulty INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS lesson_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            lesson_id TEXT NOT NULL,
            xp_earned INTEGER DEFAULT 0,
            completed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, lesson_id)
        );

        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            shares REAL NOT NULL DEFAULT 0,
            avg_price REAL NOT NULL DEFAULT 0,
            bought_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, ticker)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL,
            shares REAL NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            achievement TEXT NOT NULL,
            unlocked_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, achievement)
        );

        CREATE TABLE IF NOT EXISTS daily_missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            mission TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            UNIQUE(user_id, mission, date)
        );

        CREATE TABLE IF NOT EXISTS market_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            action TEXT,
            seen INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, event_id)
        );

        CREATE TABLE IF NOT EXISTS diary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT,
            ticker TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS streak_freezes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            used_on TEXT,
            bought_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS onboarding_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL UNIQUE,
            topic TEXT NOT NULL,
            difficulty INTEGER NOT NULL,
            qtype TEXT NOT NULL,
            scenario TEXT NOT NULL,
            question TEXT NOT NULL,
            options_json TEXT NOT NULL,
            correct_index INTEGER NOT NULL,
            weight REAL DEFAULT 1.0,
            order_no INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS onboarding_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            level_id TEXT NOT NULL,
            score REAL NOT NULL,
            topic_scores TEXT,
            answers_json TEXT,
            start_module TEXT,
            start_lesson TEXT,
            completed_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS adaptive_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            question_id TEXT,
            is_correct INTEGER NOT NULL,
            time_ms INTEGER DEFAULT 0,
            source TEXT DEFAULT 'lesson',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS topic_mastery (
            user_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            mastery REAL DEFAULT 0.0,
            answers INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, topic)
        );

        CREATE TABLE IF NOT EXISTS lesson_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            weak_topic TEXT NOT NULL,
            strong_topic TEXT NOT NULL,
            lesson_json TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, weak_topic)
        );
        """
    )
    seed_onboarding_questions(conn)
    conn.commit()
    conn.close()
