"""
JARVIS Agent State Schema
"""
from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    user_input: str
    goal: str
    plan: List[str]
    current_step: str
    tool_calls: List[Dict[str, Any]]
    observations: List[str]
    result: str
    critique: str
    needs_retry: bool
    done: bool
    memory_context: List[str]
    run_id: str
    error: Optional[str]
    iterations: int
