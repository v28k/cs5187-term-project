"""Diff coverage: how many of a commit's changed lines did the generated SQL execute?

Needs a PostgreSQL built with ``--enable-coverage`` (gcov) and running from that
build (``COVERAGE=1 bash harness/local/build_pg.sh``). Every backend writes its
counters to ``.gcda`` files next to the object files when it exits, so the
caller reconnects before measuring.

    diff coverage(commit) = |changed lines executed| / |changed lines that are executable|

Changed lines are numbered on the commit's side; if the coverage build is at a
later revision they are mapped forward through ``git diff`` (lines inside later
hunks are dropped).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def reset(build_dir: str | Path) -> int:
    """Delete all .gcda counter files under the build's backend directory."""
    n = 0
    for f in Path(build_dir, "src", "backend").rglob("*.gcda"):
        try:
            f.unlink()
            n += 1
        except FileNotFoundError:
            pass
    return n


def line_counts(build_dir: str | Path, source: str) -> dict[int, int]:
    """``{line: execution count}`` for every executable line of ``source`` (relative path)."""
    src = Path(build_dir) / source
    obj_dir = src.parent
    if not (obj_dir / (src.stem + ".gcno")).exists():
        return {}
    out = subprocess.run(["gcov", "--json-format", "--stdout", "-o", str(obj_dir), src.name],
                         cwd=obj_dir, capture_output=True, text=True, timeout=120)
    counts: dict[int, int] = {}
    for doc in out.stdout.splitlines():
        doc = doc.strip()
        if not doc.startswith("{"):
            continue
        for f in json.loads(doc).get("files", []):
            if Path(f.get("file", "")).name != src.name:
                continue
            for ln in f.get("lines", []):
                n = int(ln["line_number"])
                counts[n] = max(counts.get(n, 0), int(ln.get("count", 0)))
    return counts


def map_lines(repo: str | Path, sha: str, head: str, path: str, lines: list[int]) -> list[int]:
    """Map line numbers of ``path`` at ``sha`` to ``head`` (drops lines changed since)."""
    if not lines:
        return []
    out = subprocess.run(["git", "-C", str(repo), "diff", "-U0", f"{sha}..{head}", "--", path],
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0 or not out.stdout.strip():
        return list(lines)
    hunks = []
    for raw in out.stdout.splitlines():
        m = _HUNK.match(raw)
        if m:
            o, ol = int(m.group(1)), int(m.group(2) or 1)
            nw, nl = int(m.group(3)), int(m.group(4) or 1)
            hunks.append((o, ol, nw, nl))
    mapped = []
    for ln in lines:
        shift, dead = 0, False
        for o, ol, nw, nl in hunks:
            o_end = o + ol - 1 if ol else o - 1
            if ol and o <= ln <= o_end:
                dead = True
                break
            if (o_end if ol else o) < ln:
                shift += nl - ol
        if not dead:
            mapped.append(ln + shift)
    return mapped


def diff_coverage(build_dir: str | Path, targets: dict[str, list[int]], repo: str | Path | None = None,
                  sha: str | None = None, head: str = "HEAD") -> dict:
    covered = executable = 0
    per_file = {}
    for path, lines in targets.items():
        if repo is not None and sha is not None:
            lines = map_lines(repo, sha, head, path, lines)
        counts = line_counts(build_dir, path)
        ex = [ln for ln in lines if ln in counts]
        cov = [ln for ln in ex if counts[ln] > 0]
        per_file[path] = {"executable": len(ex), "covered": len(cov)}
        executable += len(ex)
        covered += len(cov)
    return {"covered": covered, "executable": executable,
            "ratio": round(covered / executable, 4) if executable else None, "files": per_file}
