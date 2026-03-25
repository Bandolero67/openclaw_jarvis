"""
Vision Service — Image Analysis
"""

import os
from typing import Optional


def analyze_image(image_path: str, prompt: str = "Describe this image in detail") -> str:
    """
    Analyze an image using vision-capable model.
    Falls back to simple description if no vision API available.
    """
    client = get_vision_client()
    
    if client:
        try:
            return client.analyze(image_path, prompt)
        except Exception as e:
            print(f"[vision] Error: {e}")
    
    # Fallback
    return "Image analysis not available without vision API key"


class VisionClient:
    """Vision-capable LLM client."""
    
    def __init__(self):
        self.api_key = os.getenv("VISION_API_KEY", "")
        self.provider = os.getenv("VISION_PROVIDER", "openai")  # openai, anthropic, minimax
    
    def analyze(self, image_path: str, prompt: str) -> str:
        if self.provider == "openai":
            return self._openai_vision(image_path, prompt)
        elif self.provider == "anthropic":
            return self._anthropic_vision(image_path, prompt)
        else:
            return "Unknown provider"
    
    def _openai_vision(self, image_path: str, prompt: str) -> str:
        import base64
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        
        import requests
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            },
            timeout=60
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    
    def _anthropic_vision(self, image_path: str, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        
        with open(image_path, "rb") as f:
            img_data = f.read()
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_data}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        return message.content[0].text
    
    def is_configured(self) -> bool:
        return bool(self.api_key)


_client = None

def get_vision_client() -> Optional[VisionClient]:
    global _client
    if _client is None:
        _client = VisionClient()
    return _client if _client.is_configured() else None
