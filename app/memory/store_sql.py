"""
Memory Layer — 3-Layer Memory System
A. Episodic Memory  — Was ist passiert? Tasks, Results, Errors, Iterations
B. Semantic Memory  — Was ist wichtig? Preferences, Goals, Facts
C. Procedural Memory — Wie mache ich Dinge besser? Workflows, Tool Sequences
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../data/app.db")


class MemoryType(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize full memory schema."""
    conn = get_db()
    c = conn.cursor()
    
    # Users
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT,
        created_at TEXT
    )""")
    
    # Memories (3 types)
    c.execute("""CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        type TEXT, -- episodic | semantic | procedural
        content TEXT,
        importance REAL DEFAULT 5.0,
        created_at TEXT,
        updated_at TEXT
    )""")
    
    # Tasks
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        goal TEXT,
        status TEXT DEFAULT 'pending',
        priority INTEGER DEFAULT 5,
        created_at TEXT,
        updated_at TEXT
    )""")
    
    # Runs
    c.execute("""CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        input TEXT,
        output TEXT,
        critique TEXT,
        success INTEGER DEFAULT 0,
        created_at TEXT
    )""")
    
    # Indexes for fast lookups
    c.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_runs_task ON runs(task_id)")
    
    conn.commit()
    conn.close()


# ─── EPISODIC MEMORY ──────────────────────────────────────────────────────────

def add_episode(user_id: str, content: str, importance: float = 5.0) -> str:
    """Store what happened."""
    import uuid
    eid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO memories (id, user_id, type, content, importance, created_at, updated_at)
        VALUES (?, ?, 'episodic', ?, ?, ?, ?)""",
        (eid, user_id, content, importance, now, now))
    conn.commit()
    conn.close()
    return eid


def get_episodes(user_id: str, limit: int = 20) -> List[Dict]:
    """Get recent episodes."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT * FROM memories WHERE user_id = ? AND type = 'episodic'
        ORDER BY created_at DESC LIMIT ?""", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── SEMANTIC MEMORY ─────────────────────────────────────────────────────────

def add_fact(user_id: str, content: str, importance: float = 7.0) -> str:
    """Store important fact, preference, or goal."""
    import uuid
    fid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO memories (id, user_id, type, content, importance, created_at, updated_at)
        VALUES (?, ?, 'semantic', ?, ?, ?, ?)""",
        (fid, user_id, content, importance, now, now))
    conn.commit()
    conn.close()
    return fid


def get_facts(user_id: str, limit: int = 50) -> List[Dict]:
    """Get important facts, sorted by importance."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT * FROM memories WHERE user_id = ? AND type = 'semantic'
        ORDER BY importance DESC, created_at DESC LIMIT ?""", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_fact(fact_id: str, content: str, importance: float):
    """Update a semantic memory."""
    now = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("""UPDATE memories SET content = ?, importance = ?, updated_at = ? WHERE id = ?""",
        (content, importance, now, fact_id))
    conn.commit()
    conn.close()


# ─── PROCEDURAL MEMORY ────────────────────────────────────────────────────────

def add_workflow(user_id: str, workflow: str, description: str, success_rate: float = 0.5) -> str:
    """Store how to do something better."""
    import uuid
    wid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO memories (id, user_id, type, content, importance, created_at, updated_at)
        VALUES (?, ?, 'procedural', ?, ?, ?, ?)""",
        (wid, user_id, f"{workflow}\n---\nDescription: {description}\nSuccess Rate: {success_rate}", success_rate * 10, now, now))
    conn.commit()
    conn.close()
    return wid


def get_workflows(user_id: str) -> List[Dict]:
    """Get best workflows by success rate."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT * FROM memories WHERE user_id = ? AND type = 'procedural'
        ORDER BY importance DESC""", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── TASKS ────────────────────────────────────────────────────────────────────

def create_task(user_id: str, goal: str, priority: int = 5) -> str:
    """Create a new task."""
    import uuid
    tid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO tasks (id, user_id, goal, status, priority, created_at, updated_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?)""",
        (tid, user_id, goal, priority, now, now))
    conn.commit()
    conn.close()
    return tid


def get_pending_tasks(user_id: str = None) -> List[Dict]:
    """Get pending tasks."""
    conn = get_db()
    c = conn.cursor()
    if user_id:
        c.execute("""SELECT * FROM tasks WHERE status = 'pending' AND user_id = ?
            ORDER BY priority DESC, created_at ASC""", (user_id,))
    else:
        c.execute("""SELECT * FROM tasks WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC""")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_task_status(task_id: str, status: str):
    """Update task status."""
    now = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now, task_id))
    conn.commit()
    conn.close()


# ─── RUNS ─────────────────────────────────────────────────────────────────────

def save_run(task_id: str, run_input: str, output: str, critique: str = "", success: bool = False) -> str:
    """Save a run with critique."""
    import uuid
    rid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO runs (id, task_id, input, output, critique, success, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (rid, task_id, run_input, output, critique, 1 if success else 0, now))
    conn.commit()
    conn.close()
    return rid


def get_runs(task_id: str) -> List[Dict]:
    """Get all runs for a task."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM runs WHERE task_id = ? ORDER BY created_at DESC", (task_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── MEMORY CONTEXT ───────────────────────────────────────────────────────────

def get_memory_context(user_id: str, limit: int = 20) -> List[str]:
    """Get all relevant memory as context strings for an agent."""
    facts = get_facts(user_id, limit=10)
    episodes = get_episodes(user_id, limit=5)
    workflows = get_workflows(user_id)
    
    context = []
    for f in facts:
        context.append(f"[FACT] {f['content']}")
    for e in episodes:
        context.append(f"[EPISODE] {e['content']}")
    for w in workflows[:3]:
        context.append(f"[WORKFLOW] {w['content'][:200]}")
    
    return context


# ─── SEARCH ─────────────────────────────────────────────────────────────────

def search_memory(user_id: str, query: str) -> List[Dict]:
    """Full-text search across all memory types."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT * FROM memories WHERE user_id = ? AND content LIKE ?
        ORDER BY importance DESC LIMIT 20""", (user_id, f"%{query}%"))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize
init_db()

# Also init vector memory if Redis available
try:
    from app.memory.store_vector import VectorMemory
    _vm = VectorMemory()
    print(f"[memory] Vector memory: {_vm.count()} items")
except Exception as e:
    print(f"[memory] Vector memory: not available ({e})")
