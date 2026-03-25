"""
WebSocket Server — Real-time communication
Broadcast messages to all connected clients.
"""

from fastapi import FastAPI, WebSocket
from typing import List

app = FastAPI()
clients: List[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Accept WebSocket connections."""
    await ws.accept()
    clients.append(ws)
    try:
        while True:
            # Wait for messages from client
            await ws.receive_text()
    except Exception:
        if ws in clients:
            clients.remove(ws)


async def broadcast(message: str):
    """Broadcast message to all connected clients."""
    dead = []
    for ws in clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    
    # Cleanup dead connections
    for ws in dead:
        if ws in clients:
            clients.remove(ws)


@app.get("/ws/status")
async def ws_status():
    """Check how many clients connected."""
    return {"clients": len(clients)}
