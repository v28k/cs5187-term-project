"""Mine recent PostgreSQL commits for the commit-directed LLM arm.

For each commit that touches query-processing code, the digest holds what the
model needs to propose grammar for it (message, files, changed functions, the
regression-test SQL the commit added) and what the validation gate needs to
check that the proposal reaches it: the changed lines of every ``.c`` file
(the *diff-coverage targets*).

    python -m pgfuzz llm mine ~/pgfuzz/src/postgres-master --since 2026-06-29 --out ../results/llm/commits.json
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Code whose behaviour SQL can reach and our oracles can judge.
DEFAULT_PATHS = ("src/backend/optimizer", "src/backend/executor", "src/backend/parser",
                 "src/backend/utils/adt", "src/backend/rewrite", "src/backend/nodes",
                 "src/backend/commands/explain.c", "src/backend/catalog/pg_constraint.c")
_SKIP_SUBJECT = re.compile(r"\b(typo|comment|pgindent|whitespace|doc:|docs:|translation|copyright|"
                           r"Revert\b|silence|warning|-W\w+)", re.I)
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@ ?(.*)$")
_FUNC = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")


@dataclass
class CommitDigest:
    sha: str
    date: str
    subject: str
    body: str
    files: list[str]
    functions: list[str]
    targets: dict[str, list[int]]            # .c file -> added/changed line numbers (new side)
    regress_sql: str = ""                    # SQL lines the commit added to src/test/regress/sql
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def short(self) -> str:
        return self.sha[:10]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CommitDigest":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()[:300]}")
    return out.stdout


def _changed_lines(diff: str) -> tuple[dict[str, list[int]], list[str]]:
    """New-side line numbers of added lines per .c file, and the functions the hunks are in."""
    targets: dict[str, list[int]] = {}
    funcs: list[str] = []
    cur: str | None = None
    line = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[4:].strip()
            cur = path[2:] if path.startswith("b/") else None
            continue
        m = _HUNK.match(raw)
        if m:
            line = int(m.group(1))
            ctx = m.group(3)
            f = _FUNC.search(ctx or "")
            if f and cur and cur.endswith(".c") and f.group(1) not in funcs:
                funcs.append(f.group(1))
            continue
        if cur is None or not cur.endswith(".c"):
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            text = raw[1:].strip()
            if text and not text.startswith(("/*", "*", "//")) and text not in ("{", "}"):
                targets.setdefault(cur, []).append(line)
            line += 1
        elif raw.startswith("-"):
            continue
        else:
            line += 1
    return targets, funcs


def _regress_sql(diff: str) -> str:
    out, cur = [], None
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            cur = raw[4:].strip()
            continue
        if cur and "/test/regress/sql/" in cur and raw.startswith("+") and not raw.startswith("+++"):
            out.append(raw[1:])
    return "\n".join(out).strip()


def mine(repo: str | Path, since: str, until: str = "HEAD", paths: tuple[str, ...] = DEFAULT_PATHS,
         limit: int = 200, require_test: bool = True) -> list[CommitDigest]:
    """Commits in ``since..until`` (a ref or a date) that change ``paths``.

    ``require_test`` keeps only commits that also added regression-test SQL: those
    describe the behaviour in SQL, which is what the model has to generalise."""
    repo = Path(repo)
    rng = f"{since}..{until}" if not re.match(r"\d{4}-\d\d-\d\d", since) else until
    args = ["log", "--no-merges", "--format=%H%x1f%ad%x1f%s", "--date=short"]
    if re.match(r"\d{4}-\d\d-\d\d", since):
        args.append(f"--since={since}")
    args += [rng, "--", *paths]
    digests: list[CommitDigest] = []
    for row in _git(repo, *args).splitlines():
        sha, date, subject = row.split("\x1f", 2)
        if _SKIP_SUBJECT.search(subject):
            continue
        diff = _git(repo, "show", "--format=", "-U0", "--no-color", sha)
        regress = _regress_sql(diff)
        if require_test and not regress:
            continue
        targets, funcs = _changed_lines(diff)
        targets = {f: ls for f, ls in targets.items() if any(f.startswith(p) for p in paths)}
        if not targets:
            continue
        body = _git(repo, "show", "-s", "--format=%b", sha).strip()
        files = sorted({ln[6:] for ln in diff.splitlines() if ln.startswith("+++ b/")})
        digests.append(CommitDigest(sha, date, subject, body[:3000], files, funcs[:30], targets, regress[:6000],
                                    {"target_lines": sum(len(v) for v in targets.values()), "files": len(files)}))
        if len(digests) >= limit:
            break
    return digests


def save(digests: list[CommitDigest], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps([d.to_dict() for d in digests], indent=1), encoding="utf-8")


def load(path: str | Path) -> list[CommitDigest]:
    return [CommitDigest.from_dict(d) for d in json.loads(Path(path).read_text(encoding="utf-8"))]
