"""MCP server exposing the audit as a tool. Run: uv run --project api python mcp/server.py"""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from app import store  # noqa: E402
from app.models import JURISDICTIONS, AuditRequest, Jurisdiction  # noqa: E402
from app.pipeline import run_audit  # noqa: E402
from app.report.markdown import render  # noqa: E402

server = MCPServer("groundtruth")


@server.tool()
async def audit_product(
    repo_url: str, site_url: str, policy_url: str, jurisdictions: list[Jurisdiction] | None = None
) -> str:
    """Compare what a product does (public GitHub repo + live site) with what its privacy policy says.

    Returns a Markdown report: a UK/EU/KZ matrix, findings with evidence, cited provisions and suggested fixes.
    Reports possible inconsistencies only; not legal advice.
    jurisdictions limits the matrix and verdicts to some of "UK", "EU", "KZ"; leave it out for all three.
    """
    for name, value in (("repo_url", repo_url), ("site_url", site_url), ("policy_url", policy_url)):
        if not value.startswith(("http://", "https://")):
            raise ToolError(f"{name} must be an http(s) URL")
    selected = [j for j in JURISDICTIONS if j in jurisdictions] if jurisdictions else None
    req = AuditRequest(repo_url=repo_url, site_url=site_url, policy_url=policy_url, jurisdictions=selected)
    cached = store.find_cached(req) if os.getenv("DEMO_MODE") == "cached" else None
    if cached and cached.report:
        report = cached.report
        if selected:
            report = report.model_copy(update={"matrix": [c for c in report.matrix if c.jurisdiction in selected]})
        return render(report)
    report = await run_audit(uuid.uuid4().hex[:12], req, lambda event: None)
    return render(report)


if __name__ == "__main__":
    server.run()
