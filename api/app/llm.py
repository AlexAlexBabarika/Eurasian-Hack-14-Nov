"""Anthropic client: forced tool use → Pydantic, 1 retry, on-disk response cache."""

import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

TIMEOUT_S = 60
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "llm_cache"


def model_fast() -> str:
    return os.getenv("MODEL_FAST", "claude-sonnet-5-5")


def model_strong() -> str:
    return os.getenv("MODEL_STRONG", "claude-opus-5-5")


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


async def structured[T: BaseModel](system: str, prompt: str, schema: type[T], *, model: str | None = None,
                     max_tokens: int = 4096) -> T:  # fmt: skip
    """Ask the model to fill `schema` via a forced tool call. Raises if it fails twice."""
    from anthropic import AsyncAnthropic

    model = model or model_fast()
    key = hashlib.sha256(json.dumps([model, system, prompt, schema.model_json_schema()]).encode()).hexdigest()
    cached = CACHE_DIR / f"{key}.json"
    if cached.exists():
        return schema.model_validate_json(cached.read_text())

    client = AsyncAnthropic(timeout=TIMEOUT_S, max_retries=0)
    tool = {"name": "submit", "description": f"Submit the {schema.__name__}.",
            "input_schema": schema.model_json_schema()}  # fmt: skip
    messages: list[dict] = [{"role": "user", "content": prompt}]
    last_error: Exception | None = None
    for _ in range(2):
        try:
            resp = await client.messages.create(
                model=model, max_tokens=max_tokens, system=system, messages=messages,
                tools=[tool], tool_choice={"type": "tool", "name": "submit"},
            )  # fmt: skip
            block = next(b for b in resp.content if b.type == "tool_use")
            result = schema.model_validate(block.input)
        except ValidationError as e:
            last_error = e
            messages = [{"role": "user", "content": f"{prompt}\n\nYour previous answer failed validation:\n{e}"}]
            continue
        except Exception as e:  # noqa: BLE001 - network/API errors get one retry too
            last_error = e
            continue
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_text(result.model_dump_json())
        return result
    raise RuntimeError(f"LLM call failed: {type(last_error).__name__}: {str(last_error)[:200]}")
