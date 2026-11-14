"""Call-site attribution: which data categories are passed in the arguments of calls to a vendor's SDK.

Scanner-level (no AST). Works on the output of `manifests.code_lines`, so string literal text is never data.
"""

import re
from bisect import bisect_right
from typing import NamedTuple

PII = {
    "email": re.compile(r"\be[-_]?mail\b|\$email", re.I),
    "name": re.compile(r"\b(?:full_?name|first_?name|last_?name|user\.name)\b|\$name|\bname:\s*\w+\.name", re.I),
    "phone": re.compile(r"\bphone(?:_?number)?\b", re.I),
    "location": re.compile(r"\b(?:geolocation|latitude|longitude)\b", re.I),
}
USER_CONTENT = re.compile(r"\b(?:messages|prompt|content|input)\b\s*[:=,})]", re.I)
RESOLVED_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".py"}  # others: file-level heuristic

MAX_SPAN_CHARS, MAX_SPAN_LINES = 4000, 40
MAX_CALLS = 400  # per vendor and file; with MAX_SPAN_CHARS this bounds the work on generated or adversarial input
MAX_IMPORT_LINES = 30
MAX_FLOW_LINES = 100
ENCLOSING_CHARS = 800
MIN_STEM = 5  # shortest binding name trusted to identify a local factory such as `stripeInstance()`
_NOT_CODE = ("import", "//", "#", "*", "/*")
_ID = r"[A-Za-z_$][\w$]*"
_TOKEN = re.compile(r"=>\s*\{|\)\s*\{|[()\[\]{};\n]")
_FACTORY = re.compile(r"(?:[A-Z]\w*|use[A-Z]\w*|create\w*|init\w*|client|resource)$")
_ASSIGN = re.compile(rf"^[ \t]*(?:export\s+)?(?:(?:const|let|var)\s+)?({_ID})[ \t]*(?::[^=\n]+)?=(?![=>])", re.M)
_BARE_ARG = re.compile(rf"(?:[(,{{\[:=]|\.\.\.)\s*({_ID})\s*(?=[,)}}\]])")
_JS_STATEMENT = re.compile(r"^\s*(import|export)\b(?!\s*\()", re.M)
_REQUIRE = re.compile(rf"(?:const|let|var)\s+(\{{[^}}]*\}}|{_ID})\s*=\s*(?:await\s+)?require\(")
_PY_IMPORT = re.compile(r"\s*(?:from\s+[\w.]+\s+)?import\s+(.*)", re.S)


class Hit(NamedTuple):
    category: str
    line: int  # 0-based
    via: str | None = None  # local variable the data flowed through


def clean(lines: list[str], code: list[str]) -> list[str]:
    """`code` with import and comment lines blanked."""
    return ["" if raw.lstrip().startswith(_NOT_CODE) else c for raw, c in zip(lines, code, strict=True)]


def file_level(code: list[str], ai: bool) -> list[Hit]:
    """Fallback for languages whose bindings are not resolved: any identifier in the file counts."""
    text = "\n".join(code)
    return _scan(text, _line_starts(text), [(0, len(text))], ai)


def _line_starts(text: str) -> list[int]:
    return [0] + [m.end() for m in re.finditer(r"\n", text)]


def _locals(names: str, alias: str) -> set[str]:
    """`a, b as c` / `{ a, b: c }` → the local names {a, c}."""
    parts = (re.split(alias, p)[-1].strip() for p in re.sub(r"\btype\s+|#.*|[{}()]", " ", names).split(","))
    return {p for p in parts if re.fullmatch(_ID, p)}


def import_bindings(lines: list[str], i: int, kind: str) -> set[str]:
    """Local names bound by the import on line `i`; `kind` is "es" (`from "pkg"`), "require" or "py"."""
    if kind == "py":
        stmt = lines[i]
        if "(" in stmt and ")" not in stmt:
            stmt = " ".join(lines[i : i + MAX_IMPORT_LINES]).partition(")")[0]
        m = _PY_IMPORT.match(stmt)
        if not m:
            return set()
        if stmt.lstrip().startswith("from"):
            return _locals(m.group(1), r"\s+as\s+")
        # `import a.b as c` binds c, `import a.b` binds a
        return {p.split(" as ")[-1].strip() if " as " in p else p.strip().split(".")[0] for p in m.group(1).split(",")}
    if kind == "require":
        m = _REQUIRE.search(lines[i])
        return _locals(m.group(1), ":") if m else set()
    head = "\n".join(lines[max(0, i - MAX_IMPORT_LINES) : i + 1])
    statements = list(_JS_STATEMENT.finditer(head))
    if not statements or statements[-1].group(1) == "export":  # `export { x } from "pkg"` binds nothing locally
        return set()
    clause = re.sub(r"\btype\s+", "", head[statements[-1].end() :].rpartition("from")[0])
    names = set(re.findall(rf"\*\s*as\s+({_ID})", clause))
    for braced in re.findall(r"\{([^}]*)\}", clause):
        names |= _locals(braced, r"\s+as\s+")
    default = re.match(rf"\s*({_ID})", re.sub(r"\{[^}]*\}|\*\s*as\s+\S+", "", clause))
    return names | ({default.group(1)} if default else set())


def _alternation(names: set[str]) -> str:
    return "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))


def with_instances(text: str, names: set[str]) -> set[str]:
    """Adds names assigned from `new Binding(...)`, a direct `binding(...)` call, a `binding.x.Factory(...)` call or
    a local factory named after a binding (`stripeInstance()`), and names annotated with an imported class."""
    names = set(names)
    assign = r"(?<![\w$.])([\w$.]+)\s*(?::[^=\n]+)?=\s*(?:[^;=(){}]{0,80}?[?:|&]\s*)?(?:await\s+)?"
    for _ in range(3):
        alt = _alternation(names)
        made = re.finditer(rf"{assign}(new\s+)?(?:{alt})((?:\.{_ID})*)\s*\(", text)
        found = {m.group(1) for m in made if m.group(2) or not m.group(3) or _FACTORY.search(m.group(3))}
        typed = re.finditer(rf"(?<![\w$.])({_ID})\??\s*:\s*({alt})(?![\w$.(])", text)
        found |= {m.group(1) for m in typed if m.group(2)[0].isupper()}
        if found <= names:
            break
        names |= found
    stems = [n.lower() for n in names if len(n) >= MIN_STEM and "." not in n]
    wrapped = re.finditer(rf"{assign}({_ID})\s*\(", text)
    return names | {m.group(1) for m in wrapped if any(stem in m.group(2).lower() for stem in stems)}


def _extent(text: str, starts: list[int], start: int, call: bool) -> list[tuple[int, int]]:
    """Ranges of the argument list whose `(` is at `start` (or of the expression starting there), without the
    bodies of block-bodied functions: a callback's body is not an argument."""
    last_line = min(bisect_right(starts, start) - 1 + MAX_SPAN_LINES, len(starts) - 1)
    limit = min(len(text), start + MAX_SPAN_CHARS, starts[last_line] if last_line < len(starts) - 1 else len(text))
    depth, body, last = 0, 0, start
    kept: list[tuple[int, int]] = []
    for m in _TOKEN.finditer(text, start, limit):
        tok = m.group()
        if tok in ";\n":
            if depth == 0:
                limit = m.start()
                break
            continue
        if tok[0] in ")]}":
            if body and body == depth:
                body, last = 0, m.start()
            depth -= 1
            if depth < 0 or (call and depth == 0):
                limit = m.start()
                break
        if tok[-1] in "([{":
            depth += 1
            if len(tok) > 1 and not body:
                body = depth
                kept.append((last, m.end()))
    if not body:
        kept.append((last, limit))
    return kept


def _enclosing_call(text: str, pos: int) -> int | None:
    """Offset of the `(` of the innermost call whose arguments contain `pos`."""
    depth = 0
    for m in reversed(list(re.finditer(r"[()]", text[max(0, pos - ENCLOSING_CHARS) : pos]))):
        if m.group() == ")":
            depth += 1
        elif depth:
            depth -= 1
        else:
            at = max(0, pos - ENCLOSING_CHARS) + m.start()
            return at if re.search(r"[\w$]\s*$", text[max(0, at - 40) : at]) else None
    return None


def _scan(text: str, starts: list[int], ranges: list[tuple[int, int]], ai: bool) -> list[Hit]:
    hits = []
    for cat, rx in [*PII.items(), *([("user_content", USER_CONTENT)] if ai else [])]:
        found = [m.start() for s, e in ranges if (m := rx.search(text, s, min(e + 1, len(text))))]
        if found:
            hits.append(Hit(cat, bisect_right(starts, min(found)) - 1))
    return hits


def sent(code: list[str], names: set[str], ai: bool) -> list[Hit]:
    """Categories passed to calls on `names` (the vendor's import bindings), first call site per category."""
    text = "\n".join(code)
    if not names:
        return []
    starts = _line_starts(text)
    names = with_instances(text, names)
    alt = _alternation(names)
    opens = [m.end() - 1 for m in re.finditer(rf"(?<![\w$.])(?:{alt})(?:\s*\??\.\s*{_ID}|\[[^\]\n]{{0,40}}\]|!)*\s*\(", text)]
    if ai:  # `generateText({ model: openai("gpt-4o"), prompt })`: the provider is an argument of the call that sends
        refs = (m.start() for m in re.finditer(rf"(?<![\w$.])(?:{alt})(?![\w$])", text))
        opens += [at for pos in refs if (at := _enclosing_call(text, pos)) is not None]
    assigned: dict[str, list[int]] | None = None
    best: dict[str, Hit] = {}
    for open_at in sorted(set(opens))[:MAX_CALLS]:
        ranges = _extent(text, starts, open_at, call=True)
        hits = _scan(text, starts, ranges, ai)
        direct = {h.category for h in hits}
        for s, e in ranges:  # one level of local data flow: `const props = { email }; track("x", props)`
            for m in _BARE_ARG.finditer(text, s, min(e + 1, len(text))):
                if assigned is None:
                    assigned = {}
                    for a in _ASSIGN.finditer(text):
                        assigned.setdefault(a.group(1), []).append(a.end())
                line = bisect_right(starts, m.start(1)) - 1
                before = [p for p in assigned.get(m.group(1), []) if p < open_at]
                if before and line - (bisect_right(starts, before[-1]) - 1) <= MAX_FLOW_LINES:
                    value = _extent(text, starts, before[-1], call=False)
                    hits += [Hit(h.category, line, m.group(1)) for h in _scan(text, starts, value, False)
                             if h.category not in direct]  # fmt: skip
        for h in hits:
            if h.category not in best or (h.via is None and best[h.category].via is not None):
                best[h.category] = h
    return [best[cat] for cat in [*PII, "user_content"] if cat in best]
