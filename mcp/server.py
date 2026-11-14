"""MCP server exposing the audit as a tool. Run: uv run --project api python mcp/server.py"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from app.models import AuditRequest  # noqa: E402
from app.pipeline import run_audit  # noqa: E402
from app.report.markdown import render  # noqa: E402

server = MCPServer("groundtruth")


@server.tool()
async def audit_product(policy_url: str, repo_url: str | None = None, site_url: str | None = None) -> str:
    """Compare what a product does (public GitHub repo and/or live site) with what its privacy policy says.

    Give repo_url, site_url, or both; with only one, the audit covers only what that source shows.
    Returns a Markdown report: a UK/EU/KZ matrix, findings with evidence, cited provisions and suggested fixes.
    Reports possible inconsistencies only; not legal advice.
    """
    if not repo_url and not site_url:
        raise ToolError("give a repo_url, a site_url, or both")
    for name, value in (("repo_url", repo_url), ("site_url", site_url), ("policy_url", policy_url)):
        if value and not value.startswith(("http://", "https://")):
            raise ToolError(f"{name} must be an http(s) URL")
    req = AuditRequest(repo_url=repo_url or None, site_url=site_url or None, policy_url=policy_url)
    report = await run_audit(uuid.uuid4().hex[:12], req, lambda event: None)
    return render(report)


if __name__ == "__main__":
    server.run()
