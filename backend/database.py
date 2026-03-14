import sqlite3


DB_PATH = "pulse.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS interactions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT NOT NULL,
            card_id      INTEGER NOT NULL,
            answer_index INTEGER NOT NULL,
            is_correct   INTEGER NOT NULL,
            difficulty   INTEGER NOT NULL,
            created_at   TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS progress (
            user_id          TEXT PRIMARY KEY,
            streak           INTEGER DEFAULT 0,
            correct_total    INTEGER DEFAULT 0,
            last_active_date TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            email    TEXT PRIMARY KEY,
            name     TEXT NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS lesson_completions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT NOT NULL,
            lesson_id    INTEGER NOT NULL,
            completed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, lesson_id)
        );
    """
    )
    conn.commit()
    conn.close()

