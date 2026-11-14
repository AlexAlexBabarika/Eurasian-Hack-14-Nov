"""Manifest/SDK detector: always runs. Finds catalog vendors in dependency manifests and source imports."""

import re
from pathlib import Path

from app.detect import call_sites
from app.detect.catalog import Vendor, package_index
from app.ingest.repo import RepoFile
from app.models import Evidence, Observation

MANIFESTS = {
    "package.json", "requirements.txt", "pyproject.toml", "Pipfile", "go.mod", "Gemfile",
    "pubspec.yaml", "build.gradle", "build.gradle.kts",
}  # fmt: skip
SOURCE_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".go", ".rb", ".dart", ".kt", ".java", ".vue",
              ".svelte"}  # fmt: skip

# Characters that may surround a package name inside a manifest line.
_BOUNDARY = r"""(?:^|[\s"'\[,(])"""
_END = r"""(?=$|[\s"'\],)=<>~^:;@])"""
_IMPORT = re.compile(
    r"""(?:from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\s+['"]([^'"]+)['"]"""
    r"""|^\s*(?:from|import)\s+([\w.]+))"""
)

MAX_CODE_LINE = 1000
_STRING = re.compile(r"""(?P<f>\b[fF])?(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)""")


def code_only(line: str) -> str:
    """The line without the text of string literals; interpolated expressions (`${x}`, f"{x}") are kept."""
    if len(line) > MAX_CODE_LINE:
        return ""  # minified or generated; also keeps the regex below from going quadratic on unbalanced quotes

    def repl(m: re.Match) -> str:
        s = m.group(0)
        if m.group("f"):
            return " ".join(re.findall(r"\{([^{}]*)\}", s))
        if s.startswith("`"):
            return " ".join(re.findall(r"\$\{([^{}]*)\}", s))
        return '""'

    return _STRING.sub(repl, line)


def code_lines(lines: list[str]) -> list[str]:
    """`code_only` for a whole file, also blanking the inside of multi-line template literals and docstrings."""
    out: list[str] = []
    open_delim: str | None = None  # "`", '"""' or "'''" while inside a multi-line string
    for line in lines:
        if len(line) > MAX_CODE_LINE:
            out.append("")
            continue
        if open_delim:
            before, closed, rest = line.partition(open_delim)
            interpolated = " ".join(re.findall(r"\$\{([^{}]*)\}", before)) if open_delim == "`" else ""
            if not closed:
                out.append(interpolated)
                continue
            open_delim, line, prefix = None, rest, interpolated + " "
        else:
            prefix = ""
        text = code_only(re.sub(r'"""(?:[^"\\]|\\.|"(?!""))*"""|\'\'\'(?:[^\'\\]|\\.|\'(?!\'\'))*\'\'\'', '""', line))
        for delim in ('"""', "'''", "`"):
            if delim in text:  # an opener that code_only could not pair on this line
                text, open_delim = text.partition(delim)[0], delim
                break
        out.append(prefix + text)
    return out


def _snippet(lines: list[str], idx: int, radius: int = 2) -> str:
    lo, hi = max(0, idx - radius), min(len(lines), idx + radius + 1)
    return "\n".join(line[:200] for line in lines[lo:hi])


def _manifest_hits(f: RepoFile) -> list[tuple[Vendor, int, str]]:
    hits = []
    index = package_index()
    lines = f.text.splitlines()
    for i, line in enumerate(lines):
        low = line.lower()
        for pkg, vendor in index.items():
            if pkg in low and re.search(_BOUNDARY + re.escape(pkg) + _END, low):
                hits.append((vendor, i, pkg))
    return hits


def _import_vendor(module: str) -> Vendor | None:
    index = package_index()
    module = module.lower()
    if module in index:
        return index[module]
    # "@sentry/nextjs/foo" → "@sentry/nextjs"; "openai.types" → "openai"; "posthog-js/react" → "posthog-js"
    parts = module.split("/")
    base = "/".join(parts[:2]) if module.startswith("@") else parts[0]
    return index.get(base) or index.get(module.split(".")[0])


def detect(files: list[RepoFile]) -> list[Observation]:
    by_vendor: dict[str, Observation] = {}

    def obs(v: Vendor) -> Observation:
        if v.name not in by_vendor:
            by_vendor[v.name] = Observation(
                id=f"obs-{len(by_vendor) + 1}", vendor=v.name, vendor_country=v.country,
                data_categories=list(v.categories), purpose_guess=v.purpose, is_ai=v.is_ai, evidence=[],
            )  # fmt: skip
        return by_vendor[v.name]

    def add_category(o: Observation, cat: str) -> None:
        if cat not in o.data_categories:
            o.data_categories.append(cat)

    for f in files:
        if Path(f.path).name in MANIFESTS:
            lines = f.text.splitlines()
            for vendor, i, pkg in _manifest_hits(f):
                obs(vendor).evidence.append(Evidence(
                    kind="manifest", summary=f"{pkg} declared as a dependency", file=f.path, line=i + 1,
                    snippet=lines[i].strip()[:200],
                ))  # fmt: skip

    for f in files:
        suffix = Path(f.path).suffix
        if suffix not in SOURCE_EXT:
            continue
        lines = f.text.splitlines()
        vendors: dict[str, tuple[Vendor, int, set[str]]] = {}
        for i, line in enumerate(lines):
            for m in _IMPORT.finditer(line):
                vendor = _import_vendor(next(g for g in m.groups() if g))
                # Bare `import x` is Python syntax; in JS `import Stripe from "./icons/stripe"` names a local binding.
                # Even in Python it only counts if the vendor is already known from a manifest.
                bare = m.group(4) is not None
                if vendor and (not bare or (suffix == ".py" and vendor.name in by_vendor)):
                    kind = "py" if bare else "es" if m.group(1) else "require" if m.group(2) else ""
                    names = vendors.setdefault(vendor.name, (vendor, i, set()))[2]
                    names |= call_sites.import_bindings(lines, i, kind) if kind else set()
        if not vendors:
            continue
        code = call_sites.clean(lines, code_lines(lines))  # words inside prompts and messages are not data being sent
        for vendor, i, names in vendors.values():
            o = obs(vendor)
            o.evidence.append(Evidence(
                kind="code", summary=f"{vendor.name} SDK imported", file=f.path, line=i + 1,
                snippet=_snippet(lines, i, 1),
            ))  # fmt: skip
            # A category counts as sent to the vendor when it is passed in the arguments of a call to its SDK.
            # Languages whose bindings are not resolved keep the older file-level heuristic.
            resolved = suffix in call_sites.RESOLVED_EXT
            hits = call_sites.sent(code, names, vendor.is_ai) if resolved else call_sites.file_level(code, vendor.is_ai)
            for hit in hits:
                what = "User-provided content" if hit.category == "user_content" else hit.category
                how = f"passed to {vendor.name}" if resolved else f"handled in a file that calls {vendor.name}"
                via = f" (via `{hit.via}`)" if hit.via else ""
                add_category(o, hit.category)
                o.evidence.append(Evidence(
                    kind="code", summary=f"{what} {how}{via}", file=f.path, line=hit.line + 1,
                    snippet=_snippet(lines, hit.line),
                ))  # fmt: skip
    return list(by_vendor.values())
