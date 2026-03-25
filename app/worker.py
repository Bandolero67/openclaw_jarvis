"""
JARVIS Worker — Background Scheduler Process
"""
import time
import threading
from app.agent.graph import run_agent
from app.memory.store_sql import get_pending_tasks, mark_task_done, save_insight
import uuid


class JARVISWorker:
    def __init__(self, heartbeat_interval: int = 900):
        self.heartbeat_interval = heartbeat_interval
        self.running = False
        
    def start(self):
        self.running = True
        print("[worker] Starting JARVIS worker...")
        
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        print(f"[worker] Heartbeat started (every {self.heartbeat_interval}s)")
        
        self._task_loop()
    
    def stop(self):
        self.running = False
        print("[worker] Stopping...")
    
    def _heartbeat_loop(self):
        while self.running:
            try:
                self._run_heartbeat()
            except Exception as e:
                print(f"[heartbeat] error: {e}")
            time.sleep(self.heartbeat_interval)
    
    def _run_heartbeat(self):
        pending = get_pending_tasks()
        print(f"[heartbeat] Pending tasks: {len(pending)}")
        save_insight(f"Heartbeat: {len(pending)} pending tasks", "heartbeat")
    
    def _task_loop(self):
        while self.running:
            try:
                tasks = get_pending_tasks()
                for task in tasks:
                    print(f"[worker] Processing: {task['id']}")
                    result = run_agent(task["user_input"], task["id"])
                    mark_task_done(task["id"], result)
            except Exception as e:
                print(f"[worker] Task error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    worker = JARVISWorker()
    worker.start()
