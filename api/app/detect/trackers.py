"""Map network requests and cookies recorded before consent to catalog vendors."""

from urllib.parse import urlparse

from app.detect.catalog import Vendor, load_catalog
from app.ingest.site import SiteScan
from app.models import Evidence, Observation


def _vendor_for_url(url: str) -> Vendor | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    full = (parsed.netloc + parsed.path + ("?" + parsed.query if parsed.query else "")).lower()
    for v in load_catalog():
        for d in v.domains:
            if ("/" in d and d in full) or host == d or host.endswith("." + d):
                return v
    return None


def _vendor_for_cookie(name: str) -> Vendor | None:
    return next((v for v in load_catalog() if any(name.startswith(c) for c in v.cookies)), None)


def detect(scan: SiteScan) -> list[Observation]:
    by_vendor: dict[str, Observation] = {}

    def obs(v: Vendor) -> Observation:
        if v.name not in by_vendor:
            by_vendor[v.name] = Observation(
                id=f"net-{len(by_vendor) + 1}", vendor=v.name, vendor_country=v.country,
                data_categories=list(v.categories), purpose_guess=v.purpose, is_ai=v.is_ai,
                pre_consent=True, evidence=[],
            )  # fmt: skip
        return by_vendor[v.name]

    site_host = urlparse(scan.url).netloc.lower()
    for url in scan.requests:
        if urlparse(url).netloc.lower() == site_host:
            continue
        if (v := _vendor_for_url(url)) and len(obs(v).evidence) < 4:
            obs(v).evidence.append(Evidence(
                kind="network", summary=f"Request to {v.name} before any consent interaction", url=url[:300],
            ))  # fmt: skip
    for cookie in scan.cookies:
        if v := _vendor_for_cookie(cookie):
            obs(v).evidence.append(Evidence(
                kind="cookie", summary=f"Cookie `{cookie}` ({v.name}) set before any consent interaction",
                url=scan.url,
            ))  # fmt: skip
    return list(by_vendor.values())


def merge(code: list[Observation], network: list[Observation]) -> list[Observation]:
    """One Observation per vendor; network evidence marks the vendor as pre_consent."""
    merged = {o.vendor: o.model_copy(deep=True) for o in code}
    for n in network:
        if n.vendor in merged:
            o = merged[n.vendor]
            o.pre_consent = True
            o.evidence.extend(n.evidence)
            o.data_categories.extend(c for c in n.data_categories if c not in o.data_categories)
        else:
            merged[n.vendor] = n.model_copy(deep=True)
    out = list(merged.values())
    for i, o in enumerate(out, 1):
        o.id = f"obs-{i}"
    return out
