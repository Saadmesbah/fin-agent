"""One OpenRouter transport shared by routing, SQL, and document answers."""
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


class ProviderRateLimitError(RuntimeError):
    """The provider cannot currently accept requests for the configured model."""


def complete(system: str, prompt: str, max_tokens: int = 2000) -> dict:
    load_dotenv(ROOT / ".env", encoding="utf-8-sig")
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    if not key or not model:
        raise ValueError("Set OPENROUTER_API_KEY and OPENROUTER_MODEL in .env")
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "temperature": 0,
                  "max_completion_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": prompt}]},
            timeout=(10, 120),
        )
    except requests.RequestException:
        raise RuntimeError("OpenRouter connection failed or timed out") from None
    if response.status_code == 429:
        raise ProviderRateLimitError(
            "OpenRouter HTTP 429: the configured model is rate limited. "
            "Try again when its quota resets, or configure another available model "
            "in OPENROUTER_MODEL. The data is ready, but a live answer requires the provider."
        )
    if not response.ok:
        raise RuntimeError(f"OpenRouter HTTP {response.status_code}; check model, key, credits or rate limit")
    try:
        data = response.json()
        choice = data["choices"][0]
        text = choice["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError("Unexpected OpenRouter response") from None
    if choice.get("finish_reason") == "length":
        raise RuntimeError("Model output was truncated")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Model returned no answer text")
    return {"text": text.strip(), "model": data.get("model", model),
            "usage": data.get("usage", {})}


def parse_json(text: str) -> dict:
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:-1])
    try:
        value = json.loads(text)
    except ValueError:
        raise ValueError("Model must return a valid JSON object") from None
    if not isinstance(value, dict):
        raise ValueError("Model must return a JSON object")
    return value
