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
        if e.get("fixed") and v in ("false_positive", "not_a_bug"):
            by[str(e.get("oracle") or "?")]["fixed"] += 1
    rows = []
    for name in sorted(by):
        c = by[name]
        decided = c["real"] + c["false_positive"] + c["not_a_bug"]
        rows.append({"oracle": name, "candidates": sum(c[v] for v in VERDICTS), **{v: c[v] for v in VERDICTS},
                     "fixed": c["fixed"], "precision": _ratio(c["real"], decided),
                     "precision_after_fixes": _ratio(c["real"], decided - c["fixed"])})
    tot = Counter()
    for r in rows:
        for v in (*VERDICTS, "fixed"):
            tot[v] += r[v]
    decided = tot["real"] + tot["false_positive"] + tot["not_a_bug"]
    rows.append({"oracle": "all", "candidates": sum(r["candidates"] for r in rows), **{v: tot[v] for v in VERDICTS},
                 "fixed": tot["fixed"], "precision": _ratio(tot["real"], decided),
                 "precision_after_fixes": _ratio(tot["real"], decided - tot["fixed"])})
    return rows


def _ratio(a: int, b: int) -> float | None:
    """Precision counts only decided candidates (real, false positive, not a bug);
    ``after fixes`` also leaves out false positives of classes the oracle no longer reports."""
    return round(a / b, 3) if b else None


def render_markdown(rows: list[dict[str, Any]]) -> str:
    head = ("| Oracle | Candidates | Real | Duplicate | False positive | Not a bug | Flaky | Undecided | "
            "Precision | Fixed FP classes | Precision after fixes |")
    sep = "|---|---|---|---|---|---|---|---|---|---|---|"
    lines = [head, sep]
    f = lambda x: "-" if x is None else f"{x:.2f}"
    for r in rows:
        lines.append(f"| {r['oracle']} | {r['candidates']} | {r['real']} | {r['duplicate']} | {r['false_positive']} | "
                     f"{r['not_a_bug']} | {r['flaky']} | {r['TODO']} | {f(r['precision'])} | {r['fixed']} | "
                     f"{f(r['precision_after_fixes'])} |")
    return "\n".join(lines)


def render_latex(rows: list[dict[str, Any]]) -> str:
    out = ["\\begin{tabular}{lrrrrrr}", "\\toprule",
           "Oracle & Candidates & Real & False pos. & Duplicates & Precision & After fixes \\\\", "\\midrule"]
    f = lambda x: "--" if x is None else f"{x:.2f}"
    for r in rows:
        name = r["oracle"].replace("_", "\\_")
        if r["oracle"] == "all":
            out.append("\\midrule")
        out.append(f"{name} & {r['candidates']} & {r['real']} & {r['false_positive'] + r['not_a_bug']} & "
                   f"{r['duplicate']} & {f(r['precision'])} & {f(r['precision_after_fixes'])} \\\\")
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out)
