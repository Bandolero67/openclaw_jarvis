"""
Memory Layer — SQLite Store
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../data/app.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, user_input TEXT, result TEXT, done INTEGER, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, user_input TEXT, status TEXT DEFAULT 'pending', result TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS memory (
        key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, source TEXT, created_at TEXT)""")
    conn.commit()
    conn.close()


def load_memory(state: dict) -> dict:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT key, value FROM memory ORDER BY updated_at DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    memory_context = [f"{r['key']}: {r['value']}" for r in rows]
    return {**state, "memory_context": memory_context}


def save_memory(state: dict) -> dict:
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO conversations (id, user_input, result, done, created_at)
        VALUES (?, ?, ?, ?, ?)""",
        (state.get("run_id", "?"), state.get("goal", ""), state.get("result", ""),
         1 if state.get("done") else 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return state


def add_task(user_input: str, task_id: str = None) -> str:
    import uuid
    task_id = task_id or str(uuid.uuid4())
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (id, user_input, status, created_at) VALUES (?, ?, 'pending', ?)",
        (task_id, user_input, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return task_id


def get_pending_tasks() -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_task_done(task_id: str, result: dict):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'done', result = ? WHERE id = ?", (str(result), task_id))
    conn.commit()
    conn.close()


def get_task_result(task_id: str) -> Optional[dict]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def save_insight(content: str, source: str = "system"):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO insights (content, source, created_at) VALUES (?, ?, ?)",
        (content, source, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


init_db()
