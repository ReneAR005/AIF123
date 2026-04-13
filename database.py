"""
database.py — SQLite persistence for the journal.
"""

import sqlite3
import json
import os
from datetime import datetime, date, timedelta
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), "journal_expanded.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT NOT NULL,
                time         TEXT NOT NULL,
                title        TEXT,
                content      TEXT NOT NULL,
                primary_mood TEXT NOT NULL,
                confidence   REAL,
                valence      REAL,
                arousal      REAL,
                sentiment    TEXT,
                word_count   INTEGER,
                scores_json  TEXT,
                tags         TEXT,
                created_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON entries(date)")
        conn.commit()


def save_entry(date_str, time_str, title, content, prediction, tags=None):
    tags_str = ",".join(tags) if tags else ""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO entries
                (date, time, title, content, primary_mood, confidence,
                 valence, arousal, sentiment, word_count, scores_json, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date_str, time_str, title, content,
            prediction["primary_mood"], prediction["confidence"],
            prediction["valence"], prediction["arousal"],
            prediction["sentiment_label"], prediction["word_count"],
            json.dumps(prediction["scores"]), tags_str,
        ))
        conn.commit()
        return cursor.lastrowid


def get_all_entries(limit=300):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM entries ORDER BY date DESC, time DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_entry_by_id(entry_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
    return dict(row) if row else None


def delete_entry(entry_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        conn.commit()


def update_entry(entry_id, title, content, prediction, tags=None):
    tags_str = ",".join(tags) if tags else ""
    with get_connection() as conn:
        conn.execute("""
            UPDATE entries SET title=?, content=?, primary_mood=?, confidence=?,
            valence=?, arousal=?, sentiment=?, word_count=?, scores_json=?, tags=?
            WHERE id=?
        """, (
            title, content,
            prediction["primary_mood"], prediction["confidence"],
            prediction["valence"], prediction["arousal"],
            prediction["sentiment_label"], prediction["word_count"],
            json.dumps(prediction["scores"]), tags_str, entry_id,
        ))
        conn.commit()


def search_entries(query):
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM entries
            WHERE content LIKE ? OR title LIKE ? OR tags LIKE ?
            ORDER BY date DESC LIMIT 50
        """, (q, q, q)).fetchall()
    return [dict(r) for r in rows]


def get_total_entries():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]


def get_streak():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM entries ORDER BY date DESC"
        ).fetchall()
    if not rows:
        return 0
    dates = [datetime.strptime(r["date"], "%Y-%m-%d").date() for r in rows]
    if dates[0] < date.today():
        return 0
    streak = 1
    for i in range(1, len(dates)):
        if (dates[i-1] - dates[i]).days == 1:
            streak += 1
        else:
            break
    return streak


def get_valence_timeline(days=30):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, AVG(valence) as avg_valence, AVG(arousal) as avg_arousal,
                   COUNT(*) as entries
            FROM entries WHERE date >= ?
            GROUP BY date ORDER BY date ASC
        """, (cutoff,)).fetchall()
    return [dict(r) for r in rows]


def get_mood_counts(days=30):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT primary_mood, COUNT(*) as cnt
            FROM entries WHERE date >= ?
            GROUP BY primary_mood
        """, (cutoff,)).fetchall()
    return {r["primary_mood"]: r["cnt"] for r in rows}


def get_mood_by_weekday(days=90):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT strftime('%w', date) as dow, AVG(valence) as avg_v
            FROM entries WHERE date >= ?
            GROUP BY dow ORDER BY dow
        """, (cutoff,)).fetchall()
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    return {day_names[int(r["dow"])]: r["avg_v"] for r in rows}


def get_word_count_trend(days=30):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, SUM(word_count) as total_words, COUNT(*) as entries
            FROM entries WHERE date >= ?
            GROUP BY date ORDER BY date ASC
        """, (cutoff,)).fetchall()
    return [dict(r) for r in rows]
