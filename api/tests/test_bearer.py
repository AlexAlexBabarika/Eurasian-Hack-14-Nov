"""Bearer report parsing, against the shape Bearer 2.1 actually emits for `--report dataflow --format json`."""

import asyncio
from pathlib import Path

from app.detect import bearer


def loc(file: str, line: int, **extra) -> dict:
    return {"filename": file, "full_filename": f"demo/fixture-app/{file}", "start_line_number": line, **extra}


REPORT = {
    "data_types": [
        {"name": "Email Address", "category_name": "Contact",
         "detectors": [{"name": "typescript", "locations": [loc("src/lib/analytics.ts", 7), loc("src/lib/billing.ts", 5)]}]},
        {"name": "Fullname", "category_name": "Identification",
         "detectors": [{"name": "typescript", "locations": [loc("src/lib/analytics.ts", 7)]}]},
        {"name": "IP address", "category_name": "Computer Device",
         "detectors": [{"name": "typescript", "locations": [loc("src/api/visit.ts", 3)]}]},
        {"name": "Blood Type", "category_name": "Medical and Health",
         "detectors": [{"name": "typescript", "locations": [loc("src/api/profile.ts", 9)]}]},
        {"name": "Passwords", "category_name": "Authenticating",
         "detectors": [{"name": "typescript", "locations": [loc("src/auth.ts", 2)]}]},
        {"name": "Unique Identifier", "category_name": "Identification",
         "detectors": [{"name": "typescript", "locations": [loc("src/auth.ts", 4)]}]},
    ],
    "risks": [
        {"detector_id": "javascript_lang_logger", "locations": [
            loc("src/app/api/chat/route.ts", 8,
                source={"start_line_number": 8, "content": 'console.log("chat request from", user.email, message)'},
                data_types=[{"name": "Email Address"}]),
            loc("src/app/api/chat/route.ts", 8, source={"content": "dup"}, data_types=[{"name": "Email Address"}]),
        ]},
        {"detector_id": "javascript_lang_logger_leak", "locations": [loc("src/config.ts", 3, source={})]},
        {"detector_id": "javascript_lang_hardcoded_secret", "locations": [loc("src/env.ts", 1)]},
    ],
    "components": [],
    "dependencies": [],
}  # fmt: skip


def test_data_types_map_to_policy_vocabulary():
    r = bearer.parse(REPORT)
    assert set(r.data_types) == {
        "email",
        "name",
        "ip",
        "health",
    }  # passwords / internal ids are not policy categories
    assert [(e.file, e.line) for e in r.data_types["email"]] == [
        ("src/lib/analytics.ts", 7),
        ("src/lib/billing.ts", 5),
    ]
    assert all(e.kind == "bearer" for evs in r.data_types.values() for e in evs)


def test_pii_logs_use_source_snippet_and_skip_generic_leaks():
    logs = bearer.parse(REPORT).pii_logs
    assert len(logs) == 1  # duplicate line collapsed; *_logger_leak and other security rules ignored
    assert logs[0].file == "src/app/api/chat/route.ts" and logs[0].line == 8
    assert logs[0].snippet == 'console.log("chat request from", user.email, message)'
    assert "Email Address" in logs[0].summary


def test_empty_report():
    r = bearer.parse({"data_types": None, "risks": None})
    assert r.ran and not r.data_types and not r.pii_logs


class FakeProc:
    def __init__(self, stdout: bytes, stderr: bytes = b""):
        self.out, self.err = stdout, stderr

    async def communicate(self):
        return self.out, self.err

    def kill(self):
        pass


def test_rules_for_absent_languages_are_dropped(monkeypatch):
    calls = []

    async def fake_exec(*args, **_):
        calls.append(args)
        if len(calls) == 1:
            return FakeProc(
                b"", b"Error: invalid rule IDs in only option: python_lang_logger,go_lang_logger\n"
            )
        return FakeProc(b'{"data_types": [], "risks": []}')

    monkeypatch.setattr(bearer.shutil, "which", lambda _: "/usr/bin/bearer")
    monkeypatch.setattr(bearer.asyncio, "create_subprocess_exec", fake_exec)
    r = asyncio.run(bearer.run(Path(".")))
    assert r.ran
    assert calls[1][calls[1].index("--only-rule") + 1] == "javascript_lang_logger"


def test_missing_cli_and_bad_output_never_fail(monkeypatch):
    monkeypatch.setattr(bearer.shutil, "which", lambda _: None)
    assert not asyncio.run(bearer.run(Path("."))).ran

    async def fake_exec(*_, **__):
        return FakeProc(b"not json")

    monkeypatch.setattr(bearer.shutil, "which", lambda _: "/usr/bin/bearer")
    monkeypatch.setattr(bearer.asyncio, "create_subprocess_exec", fake_exec)
    r = asyncio.run(bearer.run(Path(".")))
    assert not r.ran and "skipped" in r.message
