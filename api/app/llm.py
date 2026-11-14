"""LLM client for any OpenAI-compatible chat-completions API (OpenRouter by default).

Forced tool call → Pydantic, 1 retry, on-disk response cache.
"""

import hashlib
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

TIMEOUT_S = 60
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "llm_cache"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
ANTHROPIC_COMPAT_URL = "https://api.anthropic.com/v1"
_transport: httpx.AsyncBaseTransport | None = None  # tests inject a mock transport here


def _api_key() -> str:
    return os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""


def _direct_anthropic() -> bool:
    """Only ANTHROPIC_API_KEY is set: talk to Anthropic's OpenAI-compatible endpoint."""
    return not os.getenv("LLM_API_KEY") and bool(os.getenv("ANTHROPIC_API_KEY"))


def base_url() -> str:
    default = ANTHROPIC_COMPAT_URL if _direct_anthropic() else OPENROUTER_URL
    return (os.getenv("LLM_BASE_URL") or default).rstrip("/")


def model_fast() -> str:
    return os.getenv("MODEL_FAST") or ("claude-sonnet-5-5" if _direct_anthropic() else "anthropic/claude-sonnet-4.5")


def model_strong() -> str:
    return os.getenv("MODEL_STRONG") or model_fast()


def available() -> bool:
    return bool(_api_key())


def _openrouter_options(reasoning: bool) -> dict:
    """OpenRouter spreads calls over providers of very different speed, and reasoning models spend most of their
    output on hidden reasoning. Other OpenAI-compatible APIs may reject these fields, so they get none."""
    if not base_url().startswith(OPENROUTER_URL):
        return {}
    return {"provider": {"sort": "throughput"}} | ({} if reasoning else {"reasoning": {"enabled": False}})


async def _call(model: str, system: str, prompt: str, schema: type[BaseModel], max_tokens: int,
                reasoning: bool = True) -> dict:  # fmt: skip
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "tools": [{"type": "function", "function": {
            "name": "submit", "description": f"Submit the {schema.__name__}.",
            "parameters": schema.model_json_schema(),
        }}],
        "tool_choice": {"type": "function", "function": {"name": "submit"}},
        **_openrouter_options(reasoning),
    }  # fmt: skip
    async with httpx.AsyncClient(timeout=TIMEOUT_S, transport=_transport) as client:
        resp = await client.post(
            f"{base_url()}/chat/completions", json=body, headers={"Authorization": f"Bearer {_api_key()}"}
        )
    resp.raise_for_status()
    calls = resp.json()["choices"][0]["message"].get("tool_calls") or []
    if not calls:
        raise ValueError("model did not call the tool (does it support forced tool calls?)")
    return json.loads(calls[0]["function"]["arguments"])


async def structured[T: BaseModel](system: str, prompt: str, schema: type[T], *, model: str | None = None,
                                   max_tokens: int = 4096, reasoning: bool = True) -> T:  # fmt: skip
    """Ask the model to fill `schema` via a forced tool call. Raises if it fails twice.

    `reasoning=False` asks for the answer without hidden reasoning: for prose, not for judgement.
    """
    model = model or model_fast()
    key = hashlib.sha256(
        json.dumps([base_url(), model, system, prompt, schema.model_json_schema()]).encode()
    ).hexdigest()
    cached = CACHE_DIR / f"{key}.json"
    if cached.exists():
        return schema.model_validate_json(cached.read_text())

    attempt_prompt = prompt
    last_error: Exception | None = None
    for _ in range(2):
        try:
            result = schema.model_validate(await _call(model, system, attempt_prompt, schema, max_tokens, reasoning))
        except ValidationError as e:
            last_error = e
            attempt_prompt = f"{prompt}\n\nYour previous answer failed validation:\n{e}"
            continue
        except Exception as e:  # noqa: BLE001 - network/API/JSON errors get one retry too
            last_error = e
            continue
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_text(result.model_dump_json())
        return result
    raise RuntimeError(f"LLM call failed: {type(last_error).__name__}: {str(last_error)[:200]}")
