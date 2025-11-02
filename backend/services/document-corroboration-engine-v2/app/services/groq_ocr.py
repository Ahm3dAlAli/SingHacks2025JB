import base64
import os
from typing import Optional
import requests


GROQ_API_URL = os.environ.get("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
DEFAULT_MODEL = os.environ.get("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")


class GroqOCR:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model or DEFAULT_MODEL
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not set")

    def ocr_image_bytes(self, data: bytes, mime_type: str = "image/png") -> str:
        b64 = base64.b64encode(data).decode("ascii")
        data_url = f"data:{mime_type};base64,{b64}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract ALL legible text from this image. Return plain text only."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        }
        resp = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        js = resp.json()
        text = js["choices"][0]["message"]["content"]
        return text or ""

