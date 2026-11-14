"""llm.structured against a mocked OpenAI-compatible endpoint. No network."""

import asyncio
import json

import httpx
import pytest
from pydantic import BaseModel

from app import llm


class Answer(BaseModel):
    city: str
    population: int


def reply(arguments) -> httpx.Response:
    args = arguments if isinstance(arguments, str) else json.dumps(arguments)
    call = {"id": "1", "type": "function", "function": {"name": "submit", "arguments": args}}
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "tool_calls": [call]}}]})


@pytest.fixture
def api(monkeypatch, tmp_path):
    """Returns a function that installs canned responses and gives back the list of captured requests."""
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.test/v1")
    monkeypatch.setenv("MODEL_FAST", "vendor/model")

    def install(*responses: httpx.Response) -> list[httpx.Request]:
        queue, seen = list(responses), []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return queue.pop(0)

        monkeypatch.setattr(llm, "_transport", httpx.MockTransport(handler))
        return seen

    return install


def ask() -> Answer:
    return asyncio.run(llm.structured("system text", "user text", Answer))


def test_sends_forced_tool_call_in_openai_format(api):
    seen = api(reply({"city": "Almaty", "population": 2000000}))
    assert ask() == Answer(city="Almaty", population=2000000)
    req = seen[0]
    assert str(req.url) == "https://llm.test/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer sk-test"
    body = json.loads(req.content)
    assert body["model"] == "vendor/model"
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert body["tool_choice"] == {"type": "function", "function": {"name": "submit"}}
    assert body["tools"][0]["function"]["parameters"]["required"] == ["city", "population"]


def test_retries_once_with_the_validation_error_then_caches(api):
    seen = api(reply({"city": "Almaty"}), reply({"city": "Almaty", "population": 1}))
    assert ask().population == 1
    assert len(seen) == 2 and "failed validation" in json.loads(seen[1].content)["messages"][1]["content"]
    assert ask().population == 1 and len(seen) == 2  # second call served from cache


def test_retries_on_http_error_and_malformed_arguments(api):
    seen = api(httpx.Response(429, json={"error": "rate limited"}), reply({"city": "A", "population": 2}))
    assert ask().population == 2 and len(seen) == 2


def test_raises_after_two_failures_and_does_not_cache(api, tmp_path):
    no_tool = httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "hi"}}]})
    api(reply("{not json"), no_tool)
    with pytest.raises(RuntimeError, match="forced tool calls"):
        ask()
    assert list(tmp_path.iterdir()) == []


def test_provider_selection(monkeypatch):
    for name in ("LLM_API_KEY", "LLM_BASE_URL", "ANTHROPIC_API_KEY", "MODEL_FAST", "MODEL_STRONG"):
        monkeypatch.delenv(name, raising=False)
    assert not llm.available()
    monkeypatch.setenv("LLM_API_KEY", "sk-or")
    assert llm.available() and llm.base_url() == "https://openrouter.ai/api/v1"
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1/")
    assert llm.base_url() == "http://localhost:11434/v1"
    monkeypatch.delenv("LLM_API_KEY")
    monkeypatch.delenv("LLM_BASE_URL")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    assert llm.available() and llm.base_url() == "https://api.anthropic.com/v1"
