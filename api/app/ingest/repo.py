"""Shallow clone + bounded file walk. `repo_url` may be a GitHub URL (optionally /tree/<ref>/<subdir>) or a local dir."""

import asyncio
import os
import re
import tempfile
from pathlib import Path

from pydantic import BaseModel

CLONE_TIMEOUT_S = 30
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 3000
MAX_TEXT_BYTES = 400_000  # files larger than this are counted but not read as text
SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", ".venv", "venv", "__pycache__", "vendor", "Pods",
             ".turbo", "coverage"}  # fmt: skip
SKIP_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock", "Cargo.lock"}
_GITHUB = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/tree/([^/]+)(?:/(.+?))?)?/?$")


class RepoFile(BaseModel):
    path: str  # relative to the scanned root
    text: str


async def fetch(repo_url: str) -> Path:
    """Return a local directory containing the code to scan."""
    local = Path(repo_url.removeprefix("file://")).expanduser()
    if not repo_url.startswith("http") and local.is_dir():
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
    root = (dest / subdir).resolve() if subdir else dest
    if not root.is_dir() or not root.is_relative_to(dest.resolve()):
        raise ValueError(f"subdirectory '{subdir}' not found in repository")
    return root


def walk(root: Path) -> list[RepoFile]:
    files: list[RepoFile] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if len(files) >= MAX_FILES:
                return files
            p = Path(dirpath) / name
            try:
                size = p.stat().st_size
                if name in SKIP_NAMES or p.is_symlink() or size > MAX_FILE_BYTES:
                    continue
                raw = p.read_bytes()[:MAX_TEXT_BYTES]
            except OSError:
                continue
            if b"\0" in raw[:2048]:
                continue
            files.append(RepoFile(path=str(p.relative_to(root)), text=raw.decode("utf-8", errors="replace")))
    return files
