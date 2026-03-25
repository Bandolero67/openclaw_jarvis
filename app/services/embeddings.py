"""
Embedding Service — Generate text embeddings for vector memory

Uses OpenAI embeddings API or local model.
"""

import os
from typing import List

_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key:
                _openai_client = openai.OpenAI(api_key=api_key)
        except ImportError:
            pass
    return _openai_client


def generate_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Generate embedding for text.
    Falls back to simple hash-based if no API available.
    """
    client = get_openai_client()
    
    if client:
        try:
            response = client.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[embedding] OpenAI failed: {e}")
    
    # Fallback: simple deterministic embedding (for dev)
    return simple_embedding(text)


def simple_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Simple hash-based fallback embedding.
    NOT semantic — just for development.
    """
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    
    # Convert hash to floats
    import struct
    values = []
    for i in range(0, min(len(h), dim * 4), 4):
        val = struct.unpack('f', h[i:i+4])[0]
        values.append(val)
    
    # Pad or truncate
    while len(values) < dim:
        values.append(0.0)
    
    return values[:dim]


def batch_embed(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts."""
    return [generate_embedding(t) for t in texts]
