"""
Run Logging — Track every agent run
Stores: input, goal, plan, tools, result, critique, duration
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../data/app.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_run_logging():
    """Create run_logs table."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS run_logs (
        id TEXT PRIMARY KEY,
        input TEXT,
        goal TEXT,
        plan TEXT,
        tools_used TEXT,
        result TEXT,
        critique TEXT,
        duration_ms INTEGER,
        success INTEGER,
        created_at TEXT
    )""")
    conn.commit()
    conn.close()


def log_run(run_id: str, input: str, goal: str, plan: List[str],
            tools_used: List[str], result: str, critique: str,
            duration_ms: int, success: bool) -> str:
    """Log a complete run."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO run_logs 
        (id, input, goal, plan, tools_used, result, critique, duration_ms, success, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, input, goal, json.dumps(plan), json.dumps(tools_used),
         result, critique, duration_ms, 1 if success else 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return run_id


def get_run(run_id: str) -> Optional[Dict]:
    """Get a specific run log."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM run_logs WHERE id = ?", (run_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_runs(limit: int = 20) -> List[Dict]:
    """Get recent runs."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM run_logs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── RETRY POLICY ────────────────────────────────────────────────────────────

class RetryPolicy:
    """Retry policy for tool and model errors."""
    
    def __init__(self):
        self.max_retries = 2
        self.backoff_base = 1.5  # seconds
    
    def should_retry(self, error_type: str, attempt: int) -> bool:
        """Check if we should retry."""
        if attempt >= self.max_retries:
            return False
        
        # Tool error: retry
        if error_type == "tool_error":
            return True
        
        # Model error: change strategy
        if error_type == "model_error":
            return False  # Don't retry, change strategy
        
        # Memory conflict: mark facts, don't overwrite
        if error_type == "memory_conflict":
            return False
        
        return False
    
    def get_backoff(self, attempt: int) -> float:
        """Calculate backoff time."""
        return self.backoff_base ** attempt


# ─── PRIORITIZATION FORMULA ─────────────────────────────────────────────────

class TaskPrioritizer:
    """
    Priority = f(urgency, impact, dependency, confidence)
    
    Formula:
    priority = (urgency * 0.3) + (impact * 0.4) + (dependency * 0.2) + (confidence * 0.1)
    
    All values: 0.0 - 1.0
    """
    
    @staticmethod
    def calculate_priority(
        urgency: float,      # 0-1: how time-critical
        impact: float,       # 0-1: how much value
        dependency: float,   # 0-1: blocks other tasks
        confidence: float    # 0-1: how sure am I
    ) -> float:
        return (urgency * 0.3) + (impact * 0.4) + (dependency * 0.2) + (confidence * 0.1)
    
    @staticmethod
    def from_task(task: Dict) -> float:
        """Calculate priority from task dict."""
        return TaskPrioritizer.calculate_priority(
            urgency=task.get("urgency", 0.5),
            impact=task.get("impact", 0.5),
            dependency=task.get("dependency", 0.5),
            confidence=task.get("confidence", 0.5)
        )


# ─── SAFETY LAYER ───────────────────────────────────────────────────────────

class SafetyLayer:
    """
    Safety checks before execution:
    - Blocked commands
    - Blocked paths
    - Write permissions only in workspace
    - File versioning
    """
    
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "rm -rf ~",
        "dd if=",
        ":(){ :|:& };:",  # Fork bomb
        "curl | bash",
        "wget | bash",
    ]
    
    BLOCKED_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/root/.ssh",
        "/home/*/.ssh",
    ]
    
    WORKSPACE_ROOT = "/data/.openclaw/workspace"
    
    @classmethod
    def is_command_safe(cls, command: str) -> bool:
        """Check if command is safe."""
        cmd_lower = command.lower()
        for blocked in cls.BLOCKED_COMMANDS:
            if blocked.lower() in cmd_lower:
                return False
        return True
    
    @classmethod
    def is_path_safe(cls, path: str) -> bool:
        """Check if path is safe."""
        for blocked in cls.BLOCKED_PATHS:
            if blocked.replace("*", "") in path:
                return False
        return True
    
    @classmethod
    def can_write(cls, path: str) -> bool:
        """Only allow writes in workspace."""
        return path.startswith(cls.WORKSPACE_ROOT)
    
    @classmethod
    def validate_command(cls, command: str) -> tuple[bool, str]:
        """Validate a command. Returns (safe, reason)."""
        if not cls.is_command_safe(command):
            return False, "Command blocked: potentially destructive"
        return True, "OK"
    
    @classmethod
    def validate_path(cls, path: str, write: bool = False) -> tuple[bool, str]:
        """Validate a path. Returns (safe, reason)."""
        if not cls.is_path_safe(path):
            return False, "Path blocked: system file"
        if write and not cls.can_write(path):
            return False, f"Write only allowed in {cls.WORKSPACE_ROOT}"
        return True, "OK"


# ─── DIFF-BASED FILE EDITS ─────────────────────────────────────────────────

class DiffEditor:
    """
    Safe file editing with diff:
    1. Read file
    2. Produce diff
    3. Apply patch
    4. Validate result
    """
    
    @staticmethod
    def read(path: str) -> str:
        """Read file content."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def produce_diff(old: str, new: str, path: str) -> str:
        """Produce unified diff."""
        import difflib
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}")
        return ''.join(diff)
    
    @staticmethod
    def apply_patch(path: str, new_content: str) -> bool:
        """Apply patch to file."""
        try:
            # Backup version
            backup_path = f"{path}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(DiffEditor.read(path))
            
            # Write new content
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def edit(path: str, old_text: str, new_text: str) -> tuple[bool, str]:
        """
        Edit file with diff validation.
        Returns (success, message).
        """
        try:
            # Read current
            current = DiffEditor.read(path)
            
            # Check old text exists
            if old_text not in current:
                return False, f"Text not found in file: {old_text[:50]}..."
            
            # Produce diff
            new_content = current.replace(old_text, new_text)
            diff = DiffEditor.produce_diff(current, new_content, path)
            
            # Apply patch
            if not DiffEditor.apply_patch(path, new_content):
                return False, "Failed to write file"
            
            return True, f"Edited successfully"
        
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def restore_backup(path: str) -> bool:
        """Restore from backup."""
        backup_path = f"{path}.backup"
        try:
            with open(backup_path, 'r') as f:
                content = f.read()
            with open(path, 'w') as f:
                f.write(content)
            return True
        except:
            return False


# Initialize
init_run_logging()
