"""Fetch the policy page and extract clean main text."""

import re
from pathlib import Path

import httpx
import trafilatura

TIMEOUT_S = 20
MAX_CHARS = 40_000


def html_to_text(html: str) -> str:
    text = trafilatura.extract(html, include_comments=False, include_tables=True, favor_recall=True)
    if not text or len(text) < 200:  # fallback: crude tag strip
        body = re.sub(r"(?is)<(script|style|head|nav|footer)\b.*?</\1>", " ", html)
        text = re.sub(r"\s*\n\s*", "\n", re.sub(r"[ \t]+", " ", re.sub(r"(?s)<[^>]+>", "\n", body))).strip()
    return text[:MAX_CHARS]


async def fetch(policy_url: str) -> str:
    local = Path(policy_url.removeprefix("file://")).expanduser()
    if not policy_url.startswith("http") and local.is_file():
        return html_to_text(local.read_text())
    async with httpx.AsyncClient(timeout=TIMEOUT_S, follow_redirects=True) as client:
        resp = await client.get(policy_url, headers={"User-Agent": "Mozilla/5.0 (Groundtruth policy fetcher)"})
        resp.raise_for_status()
    text = html_to_text(resp.text)
    if len(text) < 100:
        raise ValueError("policy page has no extractable text (is it rendered client-side?)")
    return text
