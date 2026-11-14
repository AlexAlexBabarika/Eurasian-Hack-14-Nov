"""Found on Twenty: a full shallow clone (169 MB, ~40 s) cannot fit the 30 s clone limit, so nothing was scanned.

The clone now downloads only the blobs `walk()` can use. Everything runs offline against a bare repo in tmp_path.
"""

import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from app.ingest import repo

GIT = shutil.which("git") or "git"


def git(cwd: Path, *args: str) -> str:
    cmd = [GIT, "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t.test", "-c", "commit.gpgsign=false", *args]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def make_remote(tmp_path: Path, files: dict[str, bytes]) -> str:
    work, bare = tmp_path / "work", tmp_path / "remote.git"
    work.mkdir()
    git(work, "init", "-q")
    for rel, data in files.items():
        (work / rel).parent.mkdir(parents=True, exist_ok=True)
        (work / rel).write_bytes(data)
    git(work, "add", "-A", "-f")
    git(work, "commit", "-q", "-m", "init")
    git(tmp_path, "clone", "-q", "--bare", str(work), str(bare))
    git(bare, "config", "uploadpack.allowFilter", "true")
    git(bare, "config", "uploadpack.allowAnySHA1InWant", "true")
    return f"file://{bare}"


def clone(remote: str, dest: Path, subdir: str | None = None) -> Path:
    dest.mkdir()
    return asyncio.run(repo._clone(remote, None, dest, subdir))


def missing(dest: Path) -> set[str]:
    """Blob ids the clone knows about but did not download."""
    out = git(dest, "rev-list", "--objects", "--missing=print", "HEAD")
    return {line[1:] for line in out.splitlines() if line.startswith("?")}


FILES = {
    "package.json": b'{"dependencies": {"stripe": "1.0.0"}}',
    "src/app.ts": b"export const a = 1;\n",
    "public/logo.png": os.urandom(50_000),
    "yarn.lock": b"lock " * 1000,
    "node_modules/dep/index.js": b"module.exports = 2;\n",
}


def test_clone_downloads_only_what_walk_reads(tmp_path):
    remote = make_remote(tmp_path, FILES)
    root = clone(remote, tmp_path / "dest")
    files, total = repo.walk(root)
    assert {f.path: f.text for f in files} == {"package.json": FILES["package.json"].decode(),
                                               "src/app.ts": "export const a = 1;\n"}  # fmt: skip
    assert total == 2
    skipped = {git(root, "rev-parse", f"HEAD:{p}") for p in ("public/logo.png", "yarn.lock", "node_modules/dep/index.js")}
    assert missing(root) == skipped
    assert not (root / "public").exists() and not (root / "node_modules").exists()


def test_clone_caps_files_but_walk_reports_the_real_total(tmp_path, monkeypatch):
    monkeypatch.setattr(repo, "CLONE_MAX_FILES", 3)
    files = {f"src/deep/f{i}.ts": f"export const v = {i};\n".encode() for i in range(6)}
    remote = make_remote(tmp_path, {**files, "package.json": b"{}", "README.md": b"# hi\n"})
    root = clone(remote, tmp_path / "dest")
    read, total = repo.walk(root)
    assert [f.path for f in read] == ["package.json", "src/deep/f0.ts", "src/deep/f1.ts"]  # manifests, then source
    assert total == 8
    assert len(missing(root)) == 5


def test_clone_subdir_checks_out_only_that_subdir(tmp_path):
    remote = make_remote(tmp_path, {"apps/web/package.json": b"{}", "apps/web/a.ts": b"1\n", "apps/api/main.py": b"2\n"})
    root = clone(remote, tmp_path / "dest", "apps/web")
    assert root == (tmp_path / "dest" / "apps" / "web").resolve()
    assert sorted(f.path for f in repo.walk(root)[0]) == ["a.ts", "package.json"]
    assert not (tmp_path / "dest" / "apps" / "api").exists()
    with pytest.raises(ValueError, match="not found"):
        clone(remote, tmp_path / "dest2", "apps/nope")
    with pytest.raises(ValueError, match="not found"):
        clone(remote, tmp_path / "dest3", "../work")


def fake_git(tmp_path: Path, monkeypatch, body: str) -> Path:
    bin_dir, log = tmp_path / "bin", tmp_path / "calls.log"
    bin_dir.mkdir()
    (bin_dir / "git").write_text(f'#!/bin/sh\necho "$*" >> "{log}"\n{body}\n')
    (bin_dir / "git").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return log


def test_clone_falls_back_to_plain_shallow_clone_without_filter_support(tmp_path, monkeypatch):
    remote = make_remote(tmp_path, FILES)
    log = fake_git(tmp_path, monkeypatch, f'case "$*" in *--filter*) echo "unknown option" >&2; exit 129;; esac\n'
                                          f'exec "{GIT}" "$@"')  # fmt: skip
    root = clone(remote, tmp_path / "dest")
    assert (root / "public" / "logo.png").is_file()  # full checkout
    assert {f.path for f in repo.walk(root)[0]} == {"package.json", "src/app.ts"}
    assert "--filter" not in log.read_text().splitlines()[-1]


def test_git_commands_share_one_clone_budget(tmp_path, monkeypatch):
    log = fake_git(tmp_path, monkeypatch, "sleep 1")  # each command alone fits the budget, two do not
    monkeypatch.setattr(repo, "CLONE_TIMEOUT_S", 1.5)
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="git clone timed out after 1.5s"):
        clone("file:///nowhere.git", tmp_path / "dest")
    assert time.monotonic() - started < 2.5
    assert len(log.read_text().splitlines()) == 2
