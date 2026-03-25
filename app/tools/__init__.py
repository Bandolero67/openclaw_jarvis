"""
Tools Layer — Tool Categories and Selection Rules

MANDATORY
  - browser / web_fetch
  - filesystem
  - shell / exec
  - vision / image
  - scheduler / automations

OPTIONAL
  - git
  - email
  - calendar
  - notion
  - telegram
  - home_assistant
  - apis

TOOL SELECTION RULE:
  Agent soll nicht blind Tools aufrufen. Erst denken:

  1. Brauche ich wirklich ein Tool?
     → Task ohne Tool möglich? Direkt antworten.
  
  2. Welches Tool ist am sichersten?
     → Read-only zuerst: web_fetch > browser > filesystem > exec
  
  3. Welches Tool gibt mir den größten Hebel?
     → web_search: breites Wissen
     → browser: tiefe Details
     → exec: Code/Ausführung
  
  4. Wie validiere ich das Ergebnis?
     → Plausibilitätscheck
     → Quellen-Check (offizielle Quellen)
     → Mehrere Tools vergleichen
     → Selbst-Widerspruch prüfen
  
  → Use best tool for the job. Not all tools every time.
"""

from enum import Enum
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
from datetime import datetime


class ToolCategory(Enum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    LEARNED = "learned"  # Tool became good through repetition


@dataclass
class ToolDefinition:
    name: str
    category: ToolCategory
    description: str
    success_rate: float = 0.5  # Track success
    use_count: int = 0
    avg_time_ms: float = 0.0
    last_used: Optional[str] = None
    
    def record_use(self, success: bool, time_ms: float):
        """Track tool performance."""
        self.use_count += 1
        # Running average of success
        self.success_rate = (self.success_rate * (self.use_count - 1) + (1 if success else 0)) / self.use_count
        # Running average of time
        self.avg_time_ms = (self.avg_time_ms * (self.use_count - 1) + time_ms) / self.use_count
        self.last_used = datetime.utcnow().isoformat()


# ─── TOOL REGISTRY ────────────────────────────────────────────────────────────

TOOLS: Dict[str, ToolDefinition] = {
    # MANDATORY
    "browser": ToolDefinition(
        name="browser",
        category=ToolCategory.MANDATORY,
        description="Browse websites, extract content, take screenshots"
    ),
    "web_fetch": ToolDefinition(
        name="web_fetch",
        category=ToolCategory.MANDATORY,
        description="Fetch URL content, APIs, simple HTML"
    ),
    "web_search": ToolDefinition(
        name="web_search",
        category=ToolCategory.MANDATORY,
        description="Search the web for information"
    ),
    "filesystem": ToolDefinition(
        name="filesystem",
        category=ToolCategory.MANDATORY,
        description="Read, write, list files and directories"
    ),
    "shell": ToolDefinition(
        name="shell",
        category=ToolCategory.MANDATORY,
        description="Execute shell commands, scripts, programs"
    ),
    "image": ToolDefinition(
        name="image",
        category=ToolCategory.MANDATORY,
        description="Analyze images, screenshots, charts"
    ),
    "exec": ToolDefinition(
        name="exec",
        category=ToolCategory.MANDATORY,
        description="Run Python/JS code, execute binaries"
    ),
    
    # OPTIONAL
    "git": ToolDefinition(
        name="git",
        category=ToolCategory.OPTIONAL,
        description="Git operations: clone, push, pull, commit, branch"
    ),
    "email": ToolDefinition(
        name="email",
        category=ToolCategory.OPTIONAL,
        description="Send, read, search emails via SMTP/IMAP"
    ),
    "calendar": ToolDefinition(
        name="calendar",
        category=ToolCategory.OPTIONAL,
        description="Google Calendar, Outlook integration"
    ),
    "notion": ToolDefinition(
        name="notion",
        category=ToolCategory.OPTIONAL,
        description="Notion API: read/write pages, databases"
    ),
    "telegram": ToolDefinition(
        name="telegram",
        category=ToolCategory.OPTIONAL,
        description="Send/receive Telegram messages"
    ),
    "home_assistant": ToolDefinition(
        name="home_assistant",
        category=ToolCategory.OPTIONAL,
        description="Smart home control, automations"
    ),
    
    # LEARNED (from usage patterns)
    "whisper": ToolDefinition(
        name="whisper",
        category=ToolCategory.LEARNED,
        description="Audio transcription for voice messages",
        success_rate=0.95,
        use_count=5
    ),
}


# ─── TOOL SELECTION ──────────────────────────────────────────────────────────

def select_tool(task: str, context: str = "") -> str:
    """
    Select the BEST tool for the task.
    
    Rule:
      1. Is tool necessary?
      2. Is there a faster way?
      3. Did this tool work before?
      4. Track success rate
    """
    task_lower = task.lower()
    
    # Pattern matching
    if "search" in task_lower or "find" in task_lower:
        return "web_search"
    
    if "browse" in task_lower or "website" in task_lower or "fetch" in task_lower:
        return "browser"
    
    if "file" in task_lower or "read" in task_lower or "write" in task_lower:
        return "filesystem"
    
    if "command" in task_lower or "run" in task_lower or "execute" in task_lower:
        return "shell"
    
    if "image" in task_lower or "screenshot" in task_lower or "analyze" in task_lower:
        return "image"
    
    if "audio" in task_lower or "voice" in task_lower or "transcribe" in task_lower:
        return "whisper"
    
    if "email" in task_lower or "mail" in task_lower:
        return "email"
    
    if "git" in task_lower or "commit" in task_lower or "push" in task_lower:
        return "git"
    
    # Default: use success rate
    return max(
        [t for t in TOOLS.values() if t.category != ToolCategory.OPTIONAL],
        key=lambda t: t.success_rate * 0.8 + (1 if t.use_count > 0 else 0) * 0.2
    ).name


def record_tool_use(tool_name: str, success: bool, time_ms: float):
    """Record tool usage for learning."""
    if tool_name in TOOLS:
        TOOLS[tool_name].record_use(success, time_ms)


def get_tool_stats() -> List[Dict]:
    """Get tool performance stats."""
    return [
        {
            "name": t.name,
            "category": t.category.value,
            "success_rate": round(t.success_rate * 100, 1),
            "use_count": t.use_count,
            "avg_time_ms": round(t.avg_time_ms, 1),
            "last_used": t.last_used
        }
        for t in sorted(TOOLS.values(), key=lambda x: x.success_rate, reverse=True)
    ]


# ─── TOOL RESULT STANDARD ────────────────────────────────────────────────────

class ToolResult:
    """Standard tool result wrapper."""
    def __init__(self, ok: bool, output: str, meta: dict = None):
        self.ok = ok
        self.output = output
        self.meta = meta or {}
    
    def __repr__(self):
        status = "✓" if self.ok else "✗"
        return f"ToolResult({status}, {self.output[:50]}...)"
    
    def to_dict(self):
        return {"ok": self.ok, "output": self.output, "meta": self.meta}


class BaseTool:
    """Base class for all tools."""
    name = "base"
    
    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError
    
    def validate(self, **kwargs) -> bool:
        """Pre-run validation."""
        return True


# ─── CONCRETE TOOLS ──────────────────────────────────────────────────────────

class FileReadTool(BaseTool):
    name = "file_read"
    
    def run(self, path: str) -> ToolResult:
        try:
            from pathlib import Path
            content = Path(path).read_text(encoding="utf-8")
            return ToolResult(True, content, {"path": path})
        except Exception as e:
            return ToolResult(False, str(e), {"path": path})


class FileWriteTool(BaseTool):
    name = "file_write"
    
    def run(self, path: str, content: str) -> ToolResult:
        try:
            from pathlib import Path
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")
            return ToolResult(True, f"Written: {path}", {"path": path})
        except Exception as e:
            return ToolResult(False, str(e), {"path": path})


        except Exception as e:
            return ToolResult(False, str(e), {"command": command})


class WebSearchTool(BaseTool):
    name = "web_search"
    
    def run(self, query: str, max_results: int = 5) -> ToolResult:
        try:
            from app.services.llm import web_search
            results = web_search(query, max_results)
            return ToolResult(True, str(results), {"query": query, "count": len(results)})
        except Exception as e:
            return ToolResult(False, str(e), {"query": query})


class WebFetchTool(BaseTool):
    name = "web_fetch"
    
    def run(self, url: str, max_chars: int = 10000) -> ToolResult:
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8", errors="ignore")[:max_chars]
            return ToolResult(True, content, {"url": url})
        except Exception as e:
            return ToolResult(False, str(e), {"url": url})


class ImageTool(BaseTool):
    name = "image"
    
    def run(self, path: str, prompt: str = "Describe this image in detail") -> ToolResult:
        try:
            from app.services.vision import analyze_image
            result = analyze_image(path, prompt)
            return ToolResult(True, result, {"path": path})
        except Exception as e:
            return ToolResult(False, str(e), {"path": path})


# Tool registry
TOOL_CLASSES = {
    "file_read": FileReadTool,
    "file_write": FileWriteTool,
    "shell": ShellTool,
    "web_search": WebSearchTool,
    "web_fetch": WebFetchTool,
    "image": ImageTool,
}

def get_tool(name: str) -> BaseTool:
    return TOOL_CLASSES.get(name, BaseTool())()

class ShellTool(BaseTool):
    name = "shell"
    
    def run(self, command: str) -> ToolResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            output = (result.stdout or "") + (result.stderr or "")
            return ToolResult(result.returncode == 0, output, {"code": result.returncode})
        except Exception as e:
            return ToolResult(False, str(e))
