"""Playwright: load the site with a fresh profile, click nothing, record requests and cookies (pre-consent)."""

import asyncio

from pydantic import BaseModel

from app.ingest import safety

TIMEOUT_S = 15


class SiteScan(BaseModel):
    url: str
    requests: list[str] = []
    cookies: list[str] = []  # cookie names (HTTP + document.cookie)
    error: str | None = None


async def _scan(url: str) -> SiteScan:
    from playwright.async_api import async_playwright

    scan = SiteScan(url=url)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            if safety.public_mode():
                await context.route("**/*", lambda route: _guard(route, scan))
            page = await context.new_page()
            page.on("request", lambda r: scan.requests.append(r.url))
            try:
                await page.goto(url, wait_until="load", timeout=(TIMEOUT_S - 5) * 1000)
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
