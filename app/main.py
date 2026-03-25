"""
JARVIS FastAPI — API Server
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi import WebSocket
from pydantic import BaseModel
from app.agent.graph import run_agent
from app.memory.store_sql import add_task, get_task_result
from app.api.websocket import clients, broadcast
import uuid

app = FastAPI(title="JARVIS Agent")


class ChatRequest(BaseModel):
    message: str
    run_id: str = None


class ChatResponse(BaseModel):
    run_id: str
    result: str
    done: bool


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to JARVIS."""
    run_id = req.run_id or str(uuid.uuid4())
    
    result = run_agent(req.message, run_id)
    
    # Broadcast result to all WebSocket clients
    await broadcast(f"{{'run_id': '{run_id}', 'result': '{result.get('result', '')}'}}")
    
    return ChatResponse(
        run_id=result.get("run_id", run_id),
        result=result.get("result", ""),
        done=result.get("done", False)
    )


@app.get("/task/{run_id}")
async def get_task(run_id: str):
    """Get task result by run_id."""
    result = get_task_result(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "agent": "JARVIS", "ws_clients": len(clients)}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Simple dashboard."""
    return """
    <html><head><title>JARVIS</title></head>
    <body><h1>🤖 JARVIS Agent</h1>
    <p>API: POST /chat</p>
    <p>WebSocket: ws://host/ws</p>
    <p>Docs: <a href="/docs">/docs</a></p>
    </body></html>
    """
