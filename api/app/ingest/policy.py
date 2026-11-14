"""Fetch the policy page and extract clean main text."""

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

TIMEOUT_S = 20
MAX_CHARS = 40_000
MAX_LINKED_PAGES = 2
LINKED_CHARS = 5_000  # budget reserved per linked page so a long policy cannot crowd it out
LINKED_PAGE = "[Linked page:"  # marks where text from a linked subprocessor page starts
_SUBPROCESSORS = re.compile(r"sub-?processors?", re.I)
_transport: httpx.AsyncBaseTransport | None = None  # tests inject a mock transport here


def html_to_text(html: str) -> str:
    text = trafilatura.extract(html, include_comments=False, include_tables=True, favor_recall=True)
    if not text or len(text) < 200:  # fallback: crude tag strip
        body = re.sub(r"(?is)<(script|style|head|nav|footer)\b.*?</\1>", " ", html)
        text = re.sub(r"\s*\n\s*", "\n", re.sub(r"[ \t]+", " ", re.sub(r"(?s)<[^>]+>", "\n", body))).strip()
    return text


def subprocessor_links(html: str, base_url: str) -> list[str]:
    """Same-site links whose text or address says "subprocessors". Many policies keep the vendor list there."""
    site = ".".join(urlparse(base_url).netloc.lower().split(".")[-2:])
    out: list[str] = []
    for href, label in re.findall(r"""(?is)<a\b[^>]*?href=["']([^"'#]+)[^>]*>(.*?)</a>""", html):
        url = urljoin(base_url, href.strip())
        host = urlparse(url).netloc.lower()
        if not _SUBPROCESSORS.search(href + " " + re.sub(r"<[^>]+>", " ", label)):
            continue
        if url.startswith("http") and (host == site or host.endswith("." + site)) and url != base_url and url not in out:
            out.append(url)
    return out[:MAX_LINKED_PAGES]


async def fetch(policy_url: str) -> str:
    local = Path(policy_url.removeprefix("file://")).expanduser()
    if not policy_url.startswith("http") and local.is_file():
        return html_to_text(local.read_text())[:MAX_CHARS]
    headers = {"User-Agent": "Mozilla/5.0 (Groundtruth policy fetcher)"}
    async with httpx.AsyncClient(timeout=TIMEOUT_S, follow_redirects=True, transport=_transport, headers=headers) as client:
        resp = await client.get(policy_url)
        resp.raise_for_status()
        text = html_to_text(resp.text)[: MAX_CHARS - MAX_LINKED_PAGES * LINKED_CHARS]
        if len(text) < 100:
            raise ValueError("policy page has no extractable text (is it rendered client-side?)")
        for url in subprocessor_links(resp.text, str(resp.url)):
            try:
                page = await client.get(url)
                page.raise_for_status()
            except httpx.HTTPError:
                continue  # the policy page alone is still a valid input
            text += f"\n\n{LINKED_PAGE} {url}]\n{html_to_text(page.text)[:LINKED_CHARS]}"
    return text
