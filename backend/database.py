import sqlite3

DB_PATH = "pulse.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        -- Users
        CREATE TABLE IF NOT EXISTS users (
            email    TEXT PRIMARY KEY,
            name     TEXT NOT NULL,
            password TEXT NOT NULL
        );

        -- User progress & gamification
        CREATE TABLE IF NOT EXISTS progress (
            user_id          TEXT PRIMARY KEY,
            streak           INTEGER DEFAULT 0,
            correct_total    INTEGER DEFAULT 0,
            last_active_date TEXT,
            xp               INTEGER DEFAULT 0,
            level            INTEGER DEFAULT 1,
            balance          INTEGER DEFAULT 1000000,
            investor_type    TEXT DEFAULT NULL
        );

        -- Old interactions (kept for compatibility)
        CREATE TABLE IF NOT EXISTS interactions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT NOT NULL,
            card_id      INTEGER NOT NULL,
            answer_index INTEGER NOT NULL,
            is_correct   INTEGER NOT NULL,
            difficulty   INTEGER NOT NULL,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        -- Lesson completions (v2: modules + lessons)
        CREATE TABLE IF NOT EXISTS lesson_completions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT NOT NULL,
            lesson_id    TEXT NOT NULL,
            xp_earned    INTEGER DEFAULT 0,
            completed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, lesson_id)
        );

        -- Portfolio holdings
        CREATE TABLE IF NOT EXISTS portfolio (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT NOT NULL,
            ticker    TEXT NOT NULL,
            shares    REAL NOT NULL DEFAULT 0,
            avg_price REAL NOT NULL DEFAULT 0,
            bought_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, ticker)
        );

        -- Transaction history
        CREATE TABLE IF NOT EXISTS transactions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            ticker     TEXT NOT NULL,
            action     TEXT NOT NULL,
            shares     REAL NOT NULL,
            price      REAL NOT NULL,
            total      REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Achievements unlocked
        CREATE TABLE IF NOT EXISTS user_achievements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            achievement TEXT NOT NULL,
            unlocked_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, achievement)
        );

        -- Daily missions tracking
        CREATE TABLE IF NOT EXISTS daily_missions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT NOT NULL,
            mission   TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            date      TEXT NOT NULL,
            UNIQUE(user_id, mission, date)
        );

        -- Market events log
        CREATE TABLE IF NOT EXISTS market_events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            event_id   TEXT NOT NULL,
            action     TEXT,
            seen       INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, event_id)
        );

        -- Investor diary entries
        CREATE TABLE IF NOT EXISTS diary (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            title      TEXT NOT NULL,
            detail     TEXT,
            ticker     TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Price history for simulation
        CREATE TABLE IF NOT EXISTS price_history (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            price  REAL NOT NULL,
            date   TEXT NOT NULL,
            UNIQUE(ticker, date)
        );

        -- Streak freeze inventory
        CREATE TABLE IF NOT EXISTS streak_freezes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            used_on TEXT,
            bought_at TEXT DEFAULT (datetime('now'))
        );

        -- Onboarding test results
        CREATE TABLE IF NOT EXISTS onboarding_results (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       TEXT NOT NULL,
            level_id      TEXT NOT NULL,
            score         REAL NOT NULL,
            topic_scores  TEXT,
            answers_json  TEXT,
            start_module  TEXT,
            start_lesson  TEXT,
            completed_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id)
        );

        -- Adaptive learning: per-answer tracking with topic tags
        CREATE TABLE IF NOT EXISTS adaptive_answers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            topic      TEXT NOT NULL,
            question_id TEXT,
            is_correct INTEGER NOT NULL,
            time_ms    INTEGER DEFAULT 0,
            source     TEXT DEFAULT 'lesson',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Topic mastery cache (updated periodically)
        CREATE TABLE IF NOT EXISTS topic_mastery (
            user_id   TEXT NOT NULL,
            topic     TEXT NOT NULL,
            mastery   REAL DEFAULT 0.0,
            answers   INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, topic)
        );
    """
    )
    conn.commit()
    conn.close()
