"""Map network requests and cookies recorded in each consent pass to catalog vendors."""

from urllib.parse import urlparse

from app.detect.catalog import Vendor, load_catalog, vendor_by_name
from app.ingest.site import SiteScan
from app.models import Evidence, Observation

MAX_REQUESTS = 4  # network evidence kept per vendor and pass
BEFORE = "before any consent interaction"
AFTER_REJECT = "after consent was rejected"
AFTER_ACCEPT = "after consent was accepted"


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
    """Before-consent evidence marks a vendor pre_consent; after-reject evidence feeds R10; after accept is context."""
    by_vendor: dict[str, Observation] = {}
    site_host = urlparse(scan.url).netloc.lower()

    def obs(v: Vendor, pre_consent: bool) -> Observation:
        if v.name not in by_vendor:
            by_vendor[v.name] = Observation(
                id=f"net-{len(by_vendor) + 1}", vendor=v.name, vendor_country=v.country,
                data_categories=list(v.categories), purpose_guess=v.purpose, is_ai=v.is_ai,
                pre_consent=pre_consent, evidence=[],
            )  # fmt: skip
        return by_vendor[v.name]

    def record(requests: list[str], cookies: list[str], when: str, pre_consent: bool = False,
               skip: frozenset[str] = frozenset()) -> None:  # fmt: skip
        for url in requests:
            if urlparse(url).netloc.lower() == site_host:
                continue
            if (v := _vendor_for_url(url)) and v.name not in skip:
                o = obs(v, pre_consent)
                if sum(when in e.summary for e in o.evidence) < MAX_REQUESTS:
                    o.evidence.append(Evidence(kind="network", summary=f"Request to {v.name} {when}", url=url[:300]))
        for cookie in cookies:
            if (v := _vendor_for_cookie(cookie)) and v.name not in skip:
                obs(v, pre_consent).evidence.append(Evidence(
                    kind="cookie", summary=f"Cookie `{cookie}` ({v.name}) set {when}", url=scan.url,
                ))  # fmt: skip

    record(scan.requests, scan.cookies, BEFORE, pre_consent=True)
    if scan.reject and scan.reject.clicked:
        record(scan.reject.requests, scan.reject.cookies, AFTER_REJECT)
    if scan.accept and scan.accept.clicked:  # only vendors not seen without consent: these are consent-gated
        record(scan.accept.requests, scan.accept.cookies, AFTER_ACCEPT, skip=frozenset(by_vendor))
    return list(by_vendor.values())


def seen(o: Observation, when: str) -> bool:
    return any(when in e.summary for e in o.evidence if e.kind in ("network", "cookie"))


def is_tracker(o: Observation) -> bool:
    return not getattr(vendor_by_name(o.vendor), "essential", False)


def gated(o: Observation) -> bool:
    """Seen on the site only after consent was accepted."""
    return seen(o, AFTER_ACCEPT) and not o.pre_consent and not seen(o, AFTER_REJECT)


def merge(code: list[Observation], network: list[Observation]) -> list[Observation]:
    """One Observation per vendor; evidence from before any consent marks the vendor as pre_consent."""
    merged = {o.vendor: o.model_copy(deep=True) for o in code}
    for n in network:
        if n.vendor in merged:
            o = merged[n.vendor]
            o.pre_consent = o.pre_consent or n.pre_consent
            o.evidence.extend(n.evidence)
            o.data_categories.extend(c for c in n.data_categories if c not in o.data_categories)
        else:
            merged[n.vendor] = n.model_copy(deep=True)
    out = list(merged.values())
    for i, o in enumerate(out, 1):
        o.id = f"obs-{i}"
    return out
