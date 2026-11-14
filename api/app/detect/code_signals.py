"""Grep-level signals: delete-account routes and PII written to logs."""

import re
from pathlib import Path

from pydantic import BaseModel

from app.detect.manifests import SOURCE_EXT, _snippet, code_lines
from app.ingest.repo import RepoFile
from app.models import Evidence

_DELETE = re.compile(
    r"delete[-_]?(?:my[-_]?)?account|account[/_-]delete|deleteUser|delete_user|destroy_account"
    r"|\.delete\(\s*['\"][^'\"]*/(?:users?|me|account)\b|erase[-_]?(?:user|account)",
    re.I,
)
_LOG = re.compile(r"console\.(?:log|info|warn|error|debug)\(|\blogg?er\.\w+\(|\blogging\.\w+\(|\bprint\(|\blog\.\w+\(")
_PII = re.compile(r"\be[-_]?mail\b|\bphone\b|\bpassword\b|\bpassport\b", re.I)


class CodeSignals(BaseModel):
    delete_route: list[Evidence] = []
    pii_logs: list[Evidence] = []


def detect(files: list[RepoFile]) -> CodeSignals:
    out = CodeSignals()
    for f in files:
        if Path(f.path).suffix not in SOURCE_EXT:
            continue
        lines = f.text.splitlines()
        code = code_lines(lines)
        if _DELETE.search(f.path) and len(out.delete_route) < 3:
            out.delete_route.append(Evidence(kind="code", summary="Delete-account route file", file=f.path))
        for i, line in enumerate(lines):
            if _DELETE.search(line) and len(out.delete_route) < 3:
                out.delete_route.append(Evidence(
                    kind="code", summary="Delete-account code path", file=f.path, line=i + 1,
                    snippet=_snippet(lines, i),
                ))  # fmt: skip
            # The identifier must be in code: "Queued email delivery failed" logs no personal data.
            if _LOG.search(line) and (m := _PII.search(code[i])) and len(out.pii_logs) < 5:
                out.pii_logs.append(Evidence(
                    kind="code", summary=f"`{m.group(0)}` written to application logs", file=f.path,
                    line=i + 1, snippet=_snippet(lines, i),
                ))  # fmt: skip
    return out
