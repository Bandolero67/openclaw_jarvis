"""
JARVIS LangGraph — Cognitive Loop as Graph
"""
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState


def should_retry(state: AgentState) -> bool:
    return bool(state.get("needs_retry")) and not state.get("done")


def create_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    graph.add_node("load_memory", lambda s: s)
    graph.add_node("planner", lambda s: {**s, "goal": s.get("user_input", ""), "plan": ["Analyze", "Execute", "Evaluate", "Finish"]})
    graph.add_node("executor", lambda s: {**s, "result": f"Done: {s.get('current_step', '')}"})
    graph.add_node("critic", lambda s: {**s, "done": True, "needs_retry": False})
    graph.add_node("save_memory", lambda s: s)
    
    graph.add_edge("load_memory", "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "critic")
    graph.add_conditional_edges("critic", should_retry, {True: "planner", False: "save_memory"})
    graph.add_edge("save_memory", END)
    
    graph.set_entry_point("load_memory")
    return graph.compile()


_agent_graph = None

def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = create_agent_graph()
    return _agent_graph


def run_agent(user_input: str, run_id: str = None) -> AgentState:
    import uuid
    graph = get_agent_graph()
    initial_state: AgentState = {
        "user_input": user_input,
        "goal": "",
        "plan": [],
        "current_step": "",
        "tool_calls": [],
        "observations": [],
        "result": "",
        "critique": "",
        "needs_retry": False,
        "done": False,
        "memory_context": [],
        "run_id": run_id or str(uuid.uuid4()),
        "error": None,
        "iterations": 0
    }
    return graph.invoke(initial_state)
