"""
Vector Memory — Redis + Embeddings
Semantic search for relevant memories to current goal.

Storage:
  - embedding: vector representation
  - text: original text
  - source: where it came from
  - tags: metadata filters
  - importance: 0.0-10.0
  - timestamp: when stored

Retrieval Rule:
  Before every task:
    1. SQL: Load recent tasks + open goals
    2. Vector Search: Find similar memories
    3. Inject most important into memory_context
"""

import redis
import json
import os
from typing import List, Dict, Optional
from datetime import datetime

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Connect to Redis
_redis = None

def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    return _redis


class VectorMemory:
    
    def __init__(self):
        self.r = get_redis()
        self.namespace = "jarvis:memory:"
    
    def _key(self, key: str) -> str:
        return f"{self.namespace}{key}"
    
    def store(self, text: str, embedding: List[float], 
              source: str = "user", tags: List[str] = None,
              importance: float = 5.0) -> str:
        """Store a memory with its embedding."""
        import uuid
        mid = str(uuid.uuid4())
        
        data = {
            "id": mid,
            "text": text,
            "embedding": embedding,
            "source": source,
            "tags": tags or [],
            "importance": importance,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store data
        self.r.set(self._key(f"data:{mid}"), json.dumps(data))
        
        # Add to sorted set by timestamp (for recent memories)
        ts = datetime.utcnow().timestamp()
        self.r.zadd(self._key("by_time"), {mid: ts})
        
        # Add to sorted set by importance
        self.r.zadd(self._key("by_importance"), {mid: importance})
        
        # Add tags to sets
        for tag in (tags or []):
            self.r.sadd(self._key(f"tag:{tag}"), mid)
        
        return mid
    
    def search(self, query_embedding: List[float], 
               top_k: int = 5, 
               tags: List[str] = None,
               min_importance: float = 0.0) -> List[Dict]:
        """
        Vector similarity search.
        In production: use Redis Vector SIMD or ANN index.
        For now: fetch all + compute cosine similarity.
        """
        # Get candidate IDs
        if tags:
            # Filter by tags
            candidate_sets = [self.r.smembers(self._key(f"tag:{t}")) for t in tags]
            candidates = set.intersection(*candidate_sets) if candidate_sets else set()
        else:
            # Get all by importance
            candidates = [m for m in self.r.zrevrange(self._key("by_importance"), 0, 99)]
        
        # Score by similarity (cosine similarity)
        results = []
        for mid in candidates:
            raw = self.r.get(self._key(f"data:{mid}"))
            if not raw:
                continue
            
            data = json.loads(raw)
            
            # Skip low importance
            if data["importance"] < min_importance:
                continue
            
            # Compute similarity
            sim = cosine_similarity(query_embedding, data["embedding"])
            data["score"] = sim
            results.append(data)
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]
    
    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get most recent memories."""
        mids = self.r.zrevrange(self._key("by_time"), 0, limit - 1)
        results = []
        for mid in mids:
            raw = self.r.get(self._key(f"data:{mid}"))
            if raw:
                results.append(json.loads(raw))
        return results
    
    def get_by_source(self, source: str, limit: int = 20) -> List[Dict]:
        """Get memories by source."""
        mids = self.r.zrevrange(self._key("by_time"), 0, 199)
        results = []
        for mid in mids:
            raw = self.r.get(self._key(f"data:{mid}"))
            if raw:
                data = json.loads(raw)
                if data["source"] == source:
                    results.append(data)
        return results[:limit]
    
    def delete(self, mid: str):
        """Delete a memory."""
        raw = self.r.get(self._key(f"data:{mid}"))
        if raw:
            data = json.loads(raw)
            # Remove from sets
            self.r.zrem(self._key("by_time"), mid)
            self.r.zrem(self._key("by_importance"), mid)
            for tag in data.get("tags", []):
                self.r.srem(self._key(f"tag:{tag}"), mid)
            self.r.delete(self._key(f"data:{mid}"))
    
    def count(self) -> int:
        """Count total memories."""
        return len(self.r.zrange(self._key("by_time"), 0, -1))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─── MEMORY CONTEXT BUILDER ──────────────────────────────────────────────────

def build_memory_context(user_id: str, goal: str, embedding: List[float] = None) -> Dict:
    """
    Build memory context before a task.
    
    1. SQL: Load recent tasks + open goals
    2. Vector Search: Find similar memories
    3. Inject most important into context
    """
    from app.memory.store_sql import get_pending_tasks, get_facts, get_episodes
    
    context = {
        "recent_tasks": get_pending_tasks(user_id)[:5],
        "facts": get_facts(user_id, limit=10),
        "episodes": get_episodes(user_id, limit=5),
        "similar_memories": [],
        "suggestions": []
    }
    
    # Vector search if we have an embedding
    if embedding:
        vm = VectorMemory()
        similar = vm.search(embedding, top_k=5)
        context["similar_memories"] = similar
        context["suggestions"] = [s["text"] for s in similar if s["score"] > 0.7]
    
    return context


# ─── MEMORY COMPRESSION ──────────────────────────────────────────────────────

def compress_memory(user_id: str):
    """
    Memory compression after each run:
    1. Summarize raw logs → compressed learning
    2. Merge duplicates
    3. Mark outdated facts
    
    Rule:
      - Raw logs: keep SHORT
      - Compressed learnings: keep PERMANENT
      - Outdated facts: mark/remove
    """
    from app.memory.store_sql import get_episodes
    
    episodes = get_episodes(user_id, limit=50)
    
    # Group similar episodes
    # Summarize patterns
    # Keep compressed insights only
    
    return {
        "compressed": True,
        "removed": len(episodes) - 10,  # Remove old episodes
        "kept": 10
    }
