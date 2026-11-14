"""Curated corpus loader + retrieval: jurisdiction/area filter → rule tag filter → BM25. No vector DB."""

import re
from functools import lru_cache
from pathlib import Path

import yaml
from rank_bm25 import BM25Okapi

from app.models import Area, Finding, Jurisdiction, Provision

CORPUS_DIR = Path(__file__).parent / "corpus"
TOP_K = 3

# Tags each rule is about, per area. Used as a hard filter (when anything matches) and as extra BM25 query terms.
RULE_TAGS: dict[str, dict[str, list[str]]] = {
    "R1_UNDISCLOSED_PROCESSOR": {"personal_data": ["recipients", "processors"]},
    "R2_SHARING_CONTRADICTION": {"personal_data": ["sharing", "recipients", "fairness"], "consumer": ["misleading"]},
    "R3_UNDISCLOSED_DATA_CATEGORY": {"personal_data": ["data_categories", "purposes"]},
    "R4_AI_PROCESSING_UNDISCLOSED": {"ai_transparency": ["chatbot"], "personal_data": ["ai"]},
    "R5_TRACKING_BEFORE_CONSENT": {"personal_data": ["cookies", "tracking"], "consumer": ["tracking", "dark_patterns"]},
    "R6_TRANSFER_UNDISCLOSED": {"personal_data": ["transfers", "localisation"]},
    "R7_NO_DELETION_PATH": {"personal_data": ["erasure"], "consumer": ["erasure", "omission"]},
    "R8_PII_IN_LOGS": {"personal_data": ["logs", "security"]},
    "R9_NO_RETENTION_PERIOD": {"personal_data": ["retention"]},
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]{3,}", text.lower().replace("_", " "))


@lru_cache
def load_corpus() -> dict[str, Provision]:
    corpus: dict[str, Provision] = {}
    for path in sorted(CORPUS_DIR.glob("*.yaml")):
        for raw in yaml.safe_load(path.read_text()) or []:
            p = Provision(**raw)
            if p.id in corpus:
                raise ValueError(f"duplicate provision id {p.id}")
            corpus[p.id] = p
    return corpus


def retrieve(finding: Finding, jurisdiction: Jurisdiction, area: Area) -> list[Provision]:
    """Top provisions for one finding in one matrix cell. Empty if the corpus has nothing relevant."""
    pool = [p for p in load_corpus().values() if p.jurisdiction == jurisdiction and p.area == area]
    tags = RULE_TAGS.get(finding.rule, {}).get(area, [])
    tagged = [p for p in pool if set(tags) & set(p.tags)]
    if tags and not tagged:
        return []  # nothing in this jurisdiction speaks to this rule; do not pad with unrelated law
    pool = tagged or pool
    if len(pool) <= 1:
        return pool
    bm25 = BM25Okapi([_tokens(f"{p.title} {p.summary} {' '.join(p.tags)}") for p in pool])
    scores = bm25.get_scores(_tokens(f"{finding.rule} {finding.title} {' '.join(tags)}"))
    # Rank by number of matching rule tags first (deterministic), BM25 as the tie-breaker.
    ranked = sorted(zip(pool, scores, strict=True), key=lambda ps: (-len(set(tags) & set(ps[0].tags)), -ps[1]))
    return [p for p, _ in ranked[:TOP_K]]
