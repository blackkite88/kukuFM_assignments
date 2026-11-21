"""LLM completion client with caching, retries, and token logging."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

import litellm
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T", bound=BaseModel)
CACHE_DIR = Path(".cache/llm")
LOGS_DIR = Path("logs")
LOGS_FILE = LOGS_DIR / "usage.jsonl"


def _cache_key(prompt: str, model: str) -> str:
    payload = f"{model}:{prompt}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _log_usage(model: str, prompt_tokens: int, completion_tokens: int, cost: float, cached: bool) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost": cost,
        "cached": cached,
    }
    with open(LOGS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _call_litellm(model: str, messages: List[Dict[str, str]], json_mode: bool) -> Any:
    kwargs: Dict[str, Any] = {"model": model, "messages": messages}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return litellm.completion(**kwargs)


def complete(
    messages: List[Dict[str, str]],
    schema: Optional[Type[T]] = None,
    model: Optional[str] = None,
    use_cache: bool = True,
) -> Any:
    active_model = model or os.getenv("MODEL", "gemini/gemini-2.0-flash")
    raw_prompt = json.dumps(messages, sort_keys=True)
    key = _cache_key(raw_prompt, active_model)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{key}.json"

    if use_cache and cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        _log_usage(active_model, 0, 0, 0.0, True)
        raw_text = cached_data["content"]
        if schema:
            return schema.model_validate_json(raw_text)
        return raw_text

    response = _call_litellm(active_model, messages, json_mode=schema is not None)
    content = response.choices[0].message.content or "{}"
    prompt_tokens = response.usage.prompt_tokens if hasattr(response, "usage") and response.usage else 0
    completion_tokens = response.usage.completion_tokens if hasattr(response, "usage") and response.usage else 0
    try:
        cost = litellm.completion_cost(completion_response=response)
    except Exception:
        cost = 0.0

    _log_usage(active_model, prompt_tokens, completion_tokens, cost, False)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"content": content}, f)

    if schema:
        return schema.model_validate_json(content)
    return content
