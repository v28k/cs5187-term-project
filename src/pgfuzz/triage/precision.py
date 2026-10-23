"""Oracle precision from triage verdicts (RQ2).

``triage/verdicts.yaml`` holds one entry per triaged candidate::

    - signature: 3f2a...
      oracle: metamorphic:expr          # assertion | crash | internal_error | plan-variant | cross-version | metamorphic:<kind>
      verdict: real                     # real | duplicate | false_positive | not_a_bug | flaky | TODO
      note: "range containment drops NULL strictness"
      upstream: "BUG #19xxx / commit ..."

Precision of an oracle = real / (real + false_positive + not_a_bug), the share of
its decided reports that were genuine bugs. Duplicates (a real bug reported
again under another signature) count towards neither side but are listed, and
flaky / undecided entries are reported separately.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VERDICTS = ("real", "duplicate", "false_positive", "not_a_bug", "flaky", "TODO")


def load_verdicts(path: str | Path) -> list[dict[str, Any]]:
    import yaml

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    if isinstance(data, dict):
        data = data.get("verdicts") or []
    return [d for d in data if isinstance(d, dict)]


def precision_table(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, Counter[str]] = defaultdict(Counter)
    for e in entries:
        v = str(e.get("verdict") or "TODO")
        by[str(e.get("oracle") or "?")][v if v in VERDICTS else "TODO"] += 1
    rows = []
    for name in sorted(by):
        c = by[name]
        decided = c["real"] + c["false_positive"] + c["not_a_bug"]
        rows.append({"oracle": name, "candidates": sum(c.values()), **{v: c[v] for v in VERDICTS},
                     "precision": round(c["real"] / decided, 3) if decided else None})
    tot = Counter()
    for r in rows:
        for v in VERDICTS:
            tot[v] += r[v]
    decided = tot["real"] + tot["false_positive"] + tot["not_a_bug"]
    rows.append({"oracle": "all", "candidates": sum(r["candidates"] for r in rows), **{v: tot[v] for v in VERDICTS},
                 "precision": round(tot["real"] / decided, 3) if decided else None})
    return rows


def render_markdown(rows: list[dict[str, Any]]) -> str:
    head = "| Oracle | Candidates | Real | Duplicate | False positive | Not a bug | Flaky | Undecided | Precision |"
    sep = "|---|---|---|---|---|---|---|---|---|"
    lines = [head, sep]
    for r in rows:
        p = "-" if r["precision"] is None else f"{r['precision']:.2f}"
        lines.append(f"| {r['oracle']} | {r['candidates']} | {r['real']} | {r['duplicate']} | {r['false_positive']} | "
                     f"{r['not_a_bug']} | {r['flaky']} | {r['TODO']} | {p} |")
    return "\n".join(lines)


def render_latex(rows: list[dict[str, Any]]) -> str:
    out = ["\\begin{tabular}{lrrrrr}", "\\toprule",
           "Oracle & Candidates & Real & False pos. & Duplicates & Precision \\\\", "\\midrule"]
    for r in rows:
        p = "--" if r["precision"] is None else f"{r['precision']:.2f}"
        name = r["oracle"].replace("_", "\\_")
        if r["oracle"] == "all":
            out.append("\\midrule")
        out.append(f"{name} & {r['candidates']} & {r['real']} & {r['false_positive'] + r['not_a_bug']} & "
                   f"{r['duplicate']} & {p} \\\\")
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out)
