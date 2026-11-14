"""MCP server exposing the audit as a tool. Run: uv run --project api python mcp/server.py"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from app.models import AuditRequest  # noqa: E402
from app.pipeline import run_audit  # noqa: E402
from app.report.markdown import render  # noqa: E402

server = FastMCP("groundtruth")


@server.tool()
async def audit_product(repo_url: str, site_url: str, policy_url: str) -> str:
    """Compare what a product does (public GitHub repo + live site) with what its privacy policy says.

    Returns a Markdown report: a UK/EU/KZ matrix, findings with evidence, cited provisions and suggested fixes.
    Reports possible inconsistencies only; not legal advice.
    """
    for name, value in (("repo_url", repo_url), ("site_url", site_url), ("policy_url", policy_url)):
        if not value.startswith(("http://", "https://")):
            raise ValueError(f"{name} must be an http(s) URL")
    req = AuditRequest(repo_url=repo_url, site_url=site_url, policy_url=policy_url)
    report = await run_audit(uuid.uuid4().hex[:12], req, lambda event: None)
    return render(report)


if __name__ == "__main__":
    server.run()
