"""FastAPI app: routes + SSE."""

import asyncio
import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse

from app import store
from app.models import AuditCreated, AuditRequest, AuditStatus, AuditSummary, ProgressEvent
from app.pipeline import run_audit
from app.report.markdown import render
from app.store import AUDITS, AuditState

app = FastAPI(title="ProveryAI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("WEB_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
_tasks: set[asyncio.Task] = set()


async def _run(audit_id: str, req: AuditRequest) -> None:
    state = AUDITS[audit_id]
    try:
        state.report = await run_audit(audit_id, req, state.events.append)
        state.status = "done"
        store.save(state)
    except Exception as e:  # noqa: BLE001 - surface any pipeline crash to the client
        state.error = f"{type(e).__name__}: {str(e)[:300]}"
        state.status = "error"


async def _replay(audit_id: str, cached: AuditState) -> None:
    """Wi-Fi-proof demo: replay a cached audit's events with realistic delays."""
    state = AUDITS[audit_id]
    for event in cached.events:
        await asyncio.sleep(0.4 if event.status == "running" else 1.1)
        state.events.append(event)
    state.report = cached.report.model_copy(update={"id": audit_id})
    state.status = "done"


@app.post("/audits", response_model=AuditCreated)
async def create_audit(req: AuditRequest) -> AuditCreated:
    if os.getenv("ALLOW_LOCAL_INPUTS") != "1":
        for name in ("repo_url", "site_url", "policy_url"):
            if (value := getattr(req, name)) is not None and not value.startswith(("http://", "https://")):
                raise HTTPException(422, f"{name} must be an http(s) URL")
    audit_id = uuid.uuid4().hex[:12]
    AUDITS[audit_id] = AuditState()
    cached = store.find_cached(req) if os.getenv("DEMO_MODE") == "cached" else None
    task = asyncio.create_task(_replay(audit_id, cached) if cached else _run(audit_id, req))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return AuditCreated(id=audit_id)


@app.get("/audits", response_model=list[AuditSummary])
async def list_example_audits() -> list[AuditSummary]:
    """Saved demo audits (api/data/audits/demo-*.json)."""
    return store.summaries()


def _state(audit_id: str) -> AuditState:
    state = store.load(audit_id)
    if not state:
        raise HTTPException(404, "audit not found")
    return state


@app.get("/audits/{audit_id}", response_model=AuditStatus)
async def get_audit(audit_id: str) -> AuditStatus:
    state = _state(audit_id)
    return AuditStatus(status=state.status, report=state.report, error=state.error)


@app.get(
    "/audits/{audit_id}/events",
    responses={200: {"model": ProgressEvent, "description": "text/event-stream; each `progress` event carries a ProgressEvent"}},
)
async def audit_events(audit_id: str) -> EventSourceResponse:
    state = _state(audit_id)

    async def stream():
        sent = 0
        while True:
            while sent < len(state.events):
                yield {"event": "progress", "data": state.events[sent].model_dump_json()}
                sent += 1
            if state.status != "running":
                yield {"event": "end", "data": state.status}
                return
            await asyncio.sleep(0.2)

    return EventSourceResponse(stream())


@app.get("/audits/{audit_id}/report.md", response_class=PlainTextResponse)
async def audit_markdown(audit_id: str) -> PlainTextResponse:
    state = _state(audit_id)
    if not state.report:
        raise HTTPException(409, "audit is not finished")
    return PlainTextResponse(render(state.report), media_type="text/markdown; charset=utf-8")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "demo_mode": os.getenv("DEMO_MODE", "live")}
