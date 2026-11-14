"""Shallow clone + bounded file walk. `repo_url` may be a GitHub URL (optionally /tree/<ref>/<subdir>) or a local dir."""

import asyncio
import os
import re
import tempfile
from pathlib import Path

from pydantic import BaseModel

from app.ingest import safety

CLONE_TIMEOUT_S = 30
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 3000
MAX_TEXT_BYTES = 400_000  # files larger than this are counted but not read as text
SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", ".venv", "venv", "__pycache__", "vendor", "Pods",
             ".turbo", "coverage"}  # fmt: skip
MAX_CANDIDATES = 100_000
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".mp4",
                 ".mp3", ".pdf", ".zip", ".gz", ".map", ".snap", ".lock"}  # fmt: skip
# Kept in sync with detect/manifests.py (not imported: ingest must not depend on detect).
MANIFEST_NAMES = {"package.json", "requirements.txt", "pyproject.toml", "Pipfile", "go.mod", "Gemfile", "pubspec.yaml",
                  "build.gradle", "build.gradle.kts"}  # fmt: skip
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".go", ".rb", ".dart", ".kt", ".java", ".vue",
                   ".svelte"}  # fmt: skip
TEST_DIRS = {"test", "tests", "__tests__", "e2e", "spec", "fixtures", "__mocks__", "mocks", "examples", "docs"}
SKIP_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock", "Cargo.lock"}
_GITHUB = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/tree/([^/]+)(?:/(.+?))?)?/?$")


class RepoFile(BaseModel):
    path: str  # relative to the scanned root
    text: str


async def fetch(repo_url: str) -> Path:
    """Return a local directory containing the code to scan."""
    local = Path(repo_url.removeprefix("file://")).expanduser()
    if not repo_url.startswith("http"):
        safety.check_local_path()
        if local.is_dir():
            return local
    m = _GITHUB.match(repo_url.strip())
    if not m:
        raise ValueError("repo_url must be a public https://github.com/<owner>/<repo> URL")
    owner, repo, ref, subdir = m.groups()
    dest = Path(tempfile.mkdtemp(prefix="groundtruth-"))
    token = os.getenv("GITHUB_TOKEN")
    auth = f"x-access-token:{token}@" if token else ""
    cmd = ["git", "clone", "--depth", "1", "--single-branch"]
    if ref:
        cmd += ["--branch", ref]
    cmd += [f"https://{auth}github.com/{owner}/{repo}.git", str(dest)]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )  # fmt: skip
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), CLONE_TIMEOUT_S)
    except TimeoutError:
        proc.kill()
        raise TimeoutError(f"git clone timed out after {CLONE_TIMEOUT_S}s") from None
    if proc.returncode != 0:
        raise RuntimeError(f"git clone failed: {stderr.decode(errors='replace').strip()[-200:]}")
    return scan_root(dest, subdir)


def scan_root(clone_dir: Path, subdir: str | None) -> Path:
    """The directory to scan inside a clone; a subdir must exist and must not escape the clone."""
    clone_dir = clone_dir.resolve()  # temp dirs are symlinked on macOS (/var → /private/var)
    root = (clone_dir / subdir).resolve() if subdir else clone_dir
    if not root.is_dir() or not root.is_relative_to(clone_dir):
        raise ValueError(f"subdirectory '{subdir}' not found in repository")
    return root


def _priority(rel: Path) -> tuple[int, int, str]:
    """Lower sorts first: manifests, then source, then tests, then everything else; shallow before deep."""
    name, parts = rel.name, {p.lower() for p in rel.parts[:-1]}
    is_test = bool(parts & TEST_DIRS) or ".test." in name or ".spec." in name or name.startswith("test_")
    if name in MANIFEST_NAMES:
        rank = 0
    elif rel.suffix in SOURCE_SUFFIXES:
        rank = 2 if is_test else 1
    else:
        rank = 3
    return rank, len(rel.parts), str(rel)


def walk(root: Path) -> tuple[list[RepoFile], int]:
    """Returns (files read, candidate files in the repo). Over the cap, the most relevant files are kept."""
    candidates: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if name in SKIP_NAMES or p.suffix.lower() in SKIP_SUFFIXES or len(candidates) >= MAX_CANDIDATES:
                continue
            candidates.append(p.relative_to(root))
    files: list[RepoFile] = []
    for rel in sorted(candidates, key=_priority):
        if len(files) >= MAX_FILES:
            break
        p = root / rel
        try:
            if p.is_symlink() or p.stat().st_size > MAX_FILE_BYTES:
                continue
            raw = p.read_bytes()[:MAX_TEXT_BYTES]
        except OSError:
            continue
        if b"\0" in raw[:2048]:
            continue
        files.append(RepoFile(path=str(rel), text=raw.decode("utf-8", errors="replace")))
    return files, len(candidates)
