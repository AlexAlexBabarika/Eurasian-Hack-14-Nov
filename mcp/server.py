"""MCP server exposing the audit as a tool. Run: uv run --project api python mcp/server.py"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import get_args

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from mcp.server.mcpserver import Context, MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from app import store  # noqa: E402
from app.models import JURISDICTIONS, AuditReport, AuditRequest, Jurisdiction, ProgressEvent, Step  # noqa: E402
from app.pipeline import run_audit  # noqa: E402
from app.report.markdown import render  # noqa: E402

server = MCPServer("proveryai")

# Every step reports "running" and then its outcome, except the last, which reports once.
PROGRESS_TOTAL = 2 * len(get_args(Step)) - 1


async def _audit_with_progress(req: AuditRequest, ctx: Context) -> AuditReport:
    """Run a live audit, sending each pipeline event to the client as a progress notification."""
    events: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()

    async def forward() -> None:
        sent = 0
        while (event := await events.get()) is not None:
            sent += 1
            await ctx.report_progress(PROGRESS_TOTAL if event.step == "done" else sent, PROGRESS_TOTAL, event.message)

    forwarder = asyncio.create_task(forward())
    try:
        return await run_audit(uuid.uuid4().hex[:12], req, events.put_nowait)
    finally:
        events.put_nowait(None)
        await forwarder


@server.tool()
async def audit_product(
    policy_url: str,
    ctx: Context,
    repo_url: str | None = None,
    site_url: str | None = None,
    jurisdictions: list[Jurisdiction] | None = None,
) -> str:
    """Compare what a product does (public GitHub repo and/or live site) with what its privacy policy says.

    Give repo_url, site_url, or both; with only one, the audit covers only what that source shows.
    Returns a Markdown report: a UK/EU/KZ matrix, findings with evidence, cited provisions and suggested fixes.
    Reports possible inconsistencies only; not legal advice.
    jurisdictions limits the matrix and verdicts to some of "UK", "EU", "KZ"; leave it out for all three.
    """
    if not repo_url and not site_url:
        raise ToolError("give a repo_url, a site_url, or both")
    for name, value in (("repo_url", repo_url), ("site_url", site_url), ("policy_url", policy_url)):
        if value and not value.startswith(("http://", "https://")):
            raise ToolError(f"{name} must be an http(s) URL")
    selected = [j for j in JURISDICTIONS if j in jurisdictions] if jurisdictions else None
    req = AuditRequest(repo_url=repo_url or None, site_url=site_url or None, policy_url=policy_url, jurisdictions=selected)
    cached = store.find_cached(req) if os.getenv("DEMO_MODE") == "cached" else None
    if cached and cached.report:
        report = cached.report
        if selected:
            report = report.model_copy(update={"matrix": [c for c in report.matrix if c.jurisdiction in selected]})
        return render(report)
    return render(await _audit_with_progress(req, ctx))


if __name__ == "__main__":
    server.run()
