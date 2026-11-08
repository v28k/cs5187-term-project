"""Engine test suites as seeds (C6): sqllogictest and Turso ``.sqltest`` files -> seed ``.sql``.

Engines ship thousands of hand-written tests that reach optimizer paths random generation
rarely hits. This module extracts their SQL so the grammar generator can replay it as seeds
(``generator.params.seeds``; op ``seed``):

* sqllogictest dialects (DuckDB ``.test``, DataFusion ``.slt``, SQLite ``.test``): records
  ``statement ok|error|maybe`` and ``query <types> [sort]`` followed by SQL up to ``----`` or a
  blank line. Control records (``require``, ``load``, ``mode``, ``loop``/``foreach``/``endloop``,
  ``halt``, ``hash-threshold``, ``onlyif``/``skipif``) are skipped; a test that needs a
  loop, an extension or an external file is skipped as a whole (its SQL is not self-contained).
* Turso ``.sqltest``: ``test name { ... }`` blocks; the SQL between the braces.

One seed file per test file keeps a test's setup and queries together. Statements that failed
in the suite (``statement error``) are left out, because a seed whose setup fails is noise.
"""

from __future__ import annotations

import re
from pathlib import Path

_CONTROL = ("require", "load", "mode", "halt", "hash-threshold", "onlyif", "skipif", "control", "include",
            "restart", "reconnect", "concurrentloop", "unzip", "set ", "reset ", "tags", "sleep", "endloop")
_SKIP_FILE = ("loop ", "foreach ", "concurrentloop", "concurrentforeach", "require-env", "load ", "unzip", "__TEST_DIR__",
              "{UUID}", "${")


def parse_slt(text: str) -> list[str] | None:
    """Statements of a sqllogictest file in order (failing ones left out); None if the file is
    not self-contained (loops, extensions, files, environment variables)."""
    if any(m in text for m in ("\nloop ", "\nforeach ", "\nconcurrentloop", "\nconcurrentforeach", "__TEST_DIR__",
                               "\nrequire-env", "{UUID}", "\nunzip")) or text.startswith(("loop ", "foreach ")):
        return None
    if re.search(r"^require\s+(?!skip_reload|vector_size|no_alternative_verify|noforcestorage)", text, re.M):
        return None
    out: list[str] = []
    lines = text.splitlines()
    i, skip_next = 0, False
    while i < len(lines):
        s = lines[i].strip()
        head = s.split(None, 1)[0] if s else ""
        if head in ("statement", "query"):
            kind = s.split()[1] if len(s.split()) > 1 else ""
            i += 1
            sql = []
            while i < len(lines) and lines[i].strip() and lines[i].strip() != "----":
                sql.append(lines[i])
                i += 1
            if i < len(lines) and lines[i].strip() == "----":          # expected output
                while i < len(lines) and lines[i].strip():
                    i += 1
            stmt = "\n".join(sql).strip().rstrip(";").strip()
            if stmt and not skip_next and not (head == "statement" and kind == "error"):
                out.append(stmt)
            skip_next = False
            continue
        if head in ("onlyif", "skipif"):
            skip_next = True
        i += 1
    return out


def parse_sqltest(text: str) -> list[str]:
    """SQL of every ``test name { ... }`` block of a Turso ``.sqltest`` file."""
    out = []
    for m in re.finditer(r"^test\s+\S+\s*\{\n(.*?)^\}", text, re.M | re.S):
        for stmt in re.split(r";\s*\n", m.group(1)):
            stmt = stmt.strip().rstrip(";").strip()
            if stmt:
                out.append(stmt)
    return out


def import_suite(paths: list[str], out_dir: str | Path, max_statements: int = 200,
                 max_files: int | None = None) -> dict[str, int]:
    """Write one seed file per test file under ``out_dir``; return counts."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for p in map(Path, paths):
        files += sorted(p.rglob("*")) if p.is_dir() else [p]
    files = [f for f in files if f.suffix in (".test", ".slt", ".sqltest") and f.is_file()]
    stats = {"files": 0, "skipped_files": 0, "seeds": 0, "statements": 0}
    for f in files[:max_files] if max_files else files:
        stats["files"] += 1
        text = f.read_text(encoding="utf-8", errors="replace")
        stmts = parse_sqltest(text) if f.suffix == ".sqltest" else parse_slt(text)
        if not stmts:
            stats["skipped_files"] += 1
            continue
        stmts = stmts[:max_statements]
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(f.with_suffix("")).lstrip("/"))[-120:]
        (out / f"{name}.sql").write_text(f"-- imported from {f}\n" + ";\n".join(stmts) + ";\n", encoding="utf-8")
        stats["seeds"] += 1
        stats["statements"] += len(stmts)
    return stats
