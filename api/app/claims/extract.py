"""Policy text → PolicyClaims. LLM when a key is configured, keyword heuristics otherwise."""

import re
from pathlib import Path

from app import llm
from app.detect.catalog import load_catalog
from app.models import PolicyClaims

PROMPT = (Path(__file__).parents[1] / "verdict" / "prompts" / "claims.md").read_text()
MAX_CHARS = 40_000


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def validate_quotes(claims: PolicyClaims, policy_text: str) -> PolicyClaims:
    """Drop any quote that is not an exact substring of the policy (whitespace-normalised)."""
    haystack = _norm(policy_text)
    claims.quotes = {k: _norm(v) for k, v in claims.quotes.items() if v and _norm(v) in haystack}
    return claims


def _sentences(text: str) -> list[str]:
    return [s for s in (_norm(p) for p in re.split(r"(?<=[.!?])\s+|\n+", text)) if len(s) > 15]


def heuristic(policy_text: str) -> PolicyClaims:
    sents = _sentences(policy_text)
    quotes: dict[str, str] = {}

    def find(key: str, pattern: str) -> bool:
        rx = re.compile(pattern, re.I)
        hit = next((s for s in sents if rx.search(s)), None)
        if hit:
            quotes.setdefault(key, hit)
        return hit is not None

    cats = {
        "email": r"\be-?mail", "name": r"\b(?:your|full|first|last) name\b", "phone": r"\bphone|telephone",
        "usage": r"\busage\b|how you use|analytics", "device_id": r"\bdevice\b|identifier", "ip": r"\bIP address",
        "user_content": r"content you (?:create|upload|submit)|your (?:messages|notes|prompts|content)",
        "payment": r"\bpayment|billing|card details", "location": r"\blocation\b", "health": r"\bhealth\b",
    }  # fmt: skip
    data_categories = [c for c, rx in cats.items() if find("data_categories" if c == "email" else f"data_{c}", rx)]
    named = [v.name for v in load_catalog() if re.search(rf"\b{re.escape(v.name)}\b", policy_text, re.I)]

    if find("sharing_statement", r"(?:never|do(?:es)? not|don't|will not|won't) (?:sell or )?shar"):
        sharing = "no_sharing"
    elif find("sharing_statement", r"\bsell\b(?!.{0,20}\bnot\b)|share .{0,60}advertis"):
        sharing = "sells_or_shares"
    elif find("sharing_statement", r"service providers|processors|sub-?processors|third[- ]part(?:y|ies) (?:who|that|to)"):
        sharing = "processors_only"
    else:
        sharing = "unclear"

    rights = {
        "access": r"\baccess to\b|right of access|request access", "rectification": r"rectif|correct (?:your|inaccurate)",
        "erasure": r"\beras|right to (?:be forgotten|delet)|request (?:the )?deletion|delete your (?:data|account|information)",
        "restriction": r"restrict(?:ion)? of processing", "objection": r"\bobject to\b|right to object",
        "portability": r"portab",
    }  # fmt: skip
    rights_listed = [r for r, rx in rights.items() if find(f"right_{r}", rx)]
    find("deletion_method", r"delete your account|request (?:the )?deletion|account deletion|to delete your")
    return PolicyClaims(
        data_categories=data_categories,
        named_processors=named,
        sharing_statement=sharing,
        mentions_ai=find("mentions_ai", r"artificial intelligence|\bAI\b|machine learning|language model|\bLLM"),
        international_transfers=find(
            "international_transfers",
            r"international(?:ly)? transfer|transfer.{0,60}(?:outside|abroad|other countries|third countr)"
            r"|standard contractual clauses|outside (?:the )?(?:UK|EEA|EU|Kazakhstan)",
        ),
        retention_stated=find("retention_stated", r"\bretain|retention|(?:kept|stored|keep|store) .{0,40}for (?:\d|as long)"),
        rights_listed=rights_listed,
        deletion_method=quotes.get("deletion_method"),
        cookie_consent_described=find("cookie_consent_described", r"cookie.{0,120}\bconsent|\bconsent.{0,120}cookie"),
        quotes=quotes,
    )


async def extract(policy_text: str) -> tuple[PolicyClaims, str]:
    """Returns (claims, method) where method is 'llm' or 'heuristic'."""
    text = policy_text[:MAX_CHARS]
    if llm.available():
        try:
            claims = await llm.structured(PROMPT, f"<policy>\n{text}\n</policy>", PolicyClaims)
            return validate_quotes(claims, text), "llm"
        except Exception:  # noqa: BLE001 - fall back rather than fail the audit
            pass
    return validate_quotes(heuristic(text), text), "heuristic"
