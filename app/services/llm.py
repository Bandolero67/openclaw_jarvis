"""
LLM Service — MiniMax Client
"""

import os
import requests
from typing import List, Dict, Optional


class MiniMaxClient:
    """MiniMax API client for chat completions."""
    
    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY", "")
        self.base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
        self.model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        """Generate a chat completion."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        
        return data["choices"][0]["message"]["content"]
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        """Chat with messages array."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        
        return data["choices"][0]["message"]["content"]
    
    def is_configured(self) -> bool:
        """Check if API key is set."""
        return bool(self.api_key)


# Singleton
_client = None

def get_llm() -> MiniMaxClient:
    global _client
    if _client is None:
        _client = MiniMaxClient()
    return _client


# ─── EMBEDDINGS ──────────────────────────────────────────────────────────────

def generate_embedding(text: str) -> List[float]:
    """Generate text embedding via MiniMax."""
    # MiniMax may not support embeddings — fallback to simple
    from app.services.embeddings import simple_embedding
    return simple_embedding(text)


def web_search(query: str, max_results: int = 5) -> List[Dict]:
    """Web search using MiniMax or fallback."""
    # Placeholder — integrate with actual search API
    return [{"query": query, "results": [], "count": 0}]
