"""Run a live audit and save it as a cached demo: `make cache name=hoppscotch repo=... site=... policy=...`.

With DEMO_MODE=cached the API replays the saved audit when the same three URLs are submitted.
"""

import asyncio
import sys

from app import store
from app.models import AuditRequest
from app.pipeline import run_audit
from app.store import AuditState


async def build(name: str, repo_url: str, site_url: str, policy_url: str) -> AuditState:
    state = AuditState()
    req = AuditRequest(repo_url=repo_url, site_url=site_url, policy_url=policy_url)
    state.report = await run_audit(f"demo-{name}", req, state.events.append)
    state.status = "done"
    return state


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit("usage: python -m app.demo_cache <name> <repo_url> <site_url> <policy_url>")
    state = asyncio.run(build(*sys.argv[1:]))
    for event in state.events:
        if event.status != "running":
            print(f"{event.step:13s} {event.status:8s} {event.message}")
    print("saved", store.save(state, f"demo-{sys.argv[1]}"))
