"""Persistent user memory database for Mr. Agent."""
import os
import sqlite3
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "..", ".mr_agent_user.db")


def _conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                username TEXT PRIMARY KEY,
                current_role TEXT,
                target_roles TEXT,
                preferred_locations TEXT,
                core_skills TEXT,
                work_style TEXT,
                goals TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def upsert_profile(
    username,
    current_role,
    target_roles,
    preferred_locations,
    core_skills,
    work_style,
    goals,
):
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO user_profile (
                username, current_role, target_roles, preferred_locations,
                core_skills, work_style, goals, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                current_role=excluded.current_role,
                target_roles=excluded.target_roles,
                preferred_locations=excluded.preferred_locations,
                core_skills=excluded.core_skills,
                work_style=excluded.work_style,
                goals=excluded.goals,
                updated_at=excluded.updated_at
            """,
            (
                username,
                current_role,
                target_roles,
                preferred_locations,
                core_skills,
                work_style,
                goals,
                datetime.utcnow().isoformat(),
            ),
        )


def get_profile(username):
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT username, current_role, target_roles, preferred_locations,
                   core_skills, work_style, goals, updated_at
            FROM user_profile WHERE username = ?
            """,
            (username,),
        ).fetchone()
    if not row:
        return {
            "username": username,
            "current_role": "",
            "target_roles": "",
            "preferred_locations": "",
            "core_skills": "",
            "work_style": "",
            "goals": "",
            "updated_at": "",
        }
    return dict(row)


def add_note(username, note):
    note = (note or "").strip()
    if not note:
        return
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO user_notes (username, note, created_at)
            VALUES (?, ?, ?)
            """,
            (username, note, datetime.utcnow().isoformat()),
        )


def list_notes(username, limit=20):
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT note, created_at
            FROM user_notes
            WHERE username = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (username, int(limit)),
        ).fetchall()
    return [dict(r) for r in rows]


def record_interaction(username, user_message, assistant_message):
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO user_interactions (username, user_message, assistant_message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                username,
                (user_message or "").strip(),
                (assistant_message or "").strip(),
                datetime.utcnow().isoformat(),
            ),
        )


def get_recent_interactions(username, limit=10):
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT user_message, assistant_message, created_at
            FROM user_interactions
            WHERE username = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (username, int(limit)),
        ).fetchall()
    return [dict(r) for r in rows]
