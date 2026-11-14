"""Playwright, three passes in fresh profiles: before consent (click nothing), after reject, after accept."""

import asyncio
from collections.abc import Coroutine

from pydantic import BaseModel

from app.ingest import consent, safety

TIMEOUT_S = 15  # per pass
LOAD_MS, BANNER_MS, RELOAD_MS, SETTLE_MS = 5500, 1200, 3500, 1200


class ConsentPass(BaseModel):
    """What fired after the banner button was clicked (click, then reload in the same profile)."""

    clicked: str | None = None  # label of the button clicked; None = no banner button found
    requests: list[str] = []  # issued from the click onwards
    cookies: list[str] = []  # set or renewed after the click
    error: str | None = None


class SiteScan(BaseModel):
    url: str
    requests: list[str] = []
    cookies: list[str] = []  # cookie names (HTTP + document.cookie)
    error: str | None = None
    reject: ConsentPass | None = None  # None = pass not run
    accept: ConsentPass | None = None


async def _bounded(run: Coroutine, target: SiteScan | ConsentPass) -> None:
    """One pass within its budget; a failure is recorded on its own pass and never loses the other passes."""
    try:
        await asyncio.wait_for(run, TIMEOUT_S)
    except Exception as e:  # noqa: BLE001 - partial evidence is still evidence
        target.error = target.error or f"{type(e).__name__}: {str(e)[:160] or 'pass did not finish in time'}"


async def _open(browser, scan: SiteScan):  # noqa: ANN001, ANN202 - playwright Browser → (BrowserContext, Page)
    context = await browser.new_context()
    if safety.public_mode():
        await context.route("**/*", lambda route: _guard(route, scan))
    return context, await context.new_page()


async def _before(browser, scan: SiteScan) -> None:  # noqa: ANN001
    context, page = await _open(browser, scan)
    page.on("request", lambda r: scan.requests.append(r.url))
    try:
        await page.goto(scan.url, wait_until="load", timeout=(TIMEOUT_S - 5) * 1000)
        await page.wait_for_timeout(2500)  # let async trackers fire
    except Exception as e:  # noqa: BLE001 - partial evidence is still evidence
        scan.error = scan.error or f"{type(e).__name__}: page did not finish loading"
    names = {c["name"] for c in await context.cookies()}
    try:
        doc_cookie = await page.evaluate("document.cookie")
        names |= {part.split("=")[0].strip() for part in doc_cookie.split(";") if part.strip()}
    except Exception:  # noqa: BLE001
        pass
    scan.cookies = sorted(names)


async def _after(browser, scan: SiteScan, choice: consent.Choice, out: ConsentPass) -> None:  # noqa: ANN001
    context, page = await _open(browser, scan)
    recording = False  # only what is issued from the click onwards counts, not the first page load
    page.on("request", lambda r: recording and out.requests.append(r.url))
    try:
        await page.goto(scan.url, wait_until="load", timeout=LOAD_MS)
    except Exception as e:  # noqa: BLE001 - the banner may be there even if the page is still loading
        out.error = f"{type(e).__name__}: page did not finish loading"
    for _ in range(2):  # banners are often injected late
        await page.wait_for_timeout(BANNER_MS)
        held = {c["name"]: (c["value"], c.get("expires")) for c in await context.cookies()}
        recording = True
        if label := await consent.click(page, choice):
            break
        recording = False
        out.requests.clear()
    else:
        return
    out.clicked = label
    await page.wait_for_timeout(SETTLE_MS)  # let the choice be stored
    try:
        await page.reload(wait_until="load", timeout=RELOAD_MS)  # the stored choice now applies from the first byte
        await page.wait_for_timeout(SETTLE_MS)
    except Exception as e:  # noqa: BLE001
        out.error = out.error or f"{type(e).__name__}: reload after {choice} did not finish"
    now = await context.cookies()
    out.cookies = sorted({c["name"] for c in now if held.get(c["name"]) != (c["value"], c.get("expires"))})


async def _scan(url: str) -> SiteScan:
    from playwright.async_api import async_playwright

    scan = SiteScan(url=url, reject=ConsentPass(), accept=ConsentPass())
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            await asyncio.gather(
                _bounded(_before(browser, scan), scan),
                _bounded(_after(browser, scan, "reject", scan.reject), scan.reject),
                _bounded(_after(browser, scan, "accept", scan.accept), scan.accept),
            )
        finally:
            await browser.close()
    return scan


async def _guard(route, scan: SiteScan) -> None:  # noqa: ANN001 - playwright Route
    """Public mode: navigations (incl. redirects) are fully checked; subresources only for local IPs and names."""
    req = route.request
    try:
        if req.is_navigation_request():
            await safety.check_url(req.url)
        elif safety.literal_local(req.url):
            raise safety.UnsafeURL("local address")
    except safety.UnsafeURL as e:
        if req.is_navigation_request() and req.frame.parent_frame is None:
            scan.error = f"UnsafeURL: {e}"
        await route.abort("blockedbyclient")
        return
    await route.continue_()


async def scan(url: str) -> SiteScan:
    try:
        await safety.check_url(url)
        return await asyncio.wait_for(_scan(url), TIMEOUT_S + 10)
    except Exception as e:  # noqa: BLE001 - site scan is best-effort
        return SiteScan(url=url, error=f"{type(e).__name__}: {str(e)[:200]}")
