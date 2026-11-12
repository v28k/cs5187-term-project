#!/usr/bin/env python3
"""RQ8: do composed rule kernels reach more rule pairs than plain grammar generation?

Reads the trial summaries of a two-arm kernel experiment (configs/<engine>_kernels.yaml:
arm ``grammar_mm`` vs ``grammar_kernels``) and prints a markdown table with the median per arm,
the Mann-Whitney U p-value and the Vargha-Delaney A12 effect size (kernels vs plain).

    python3 scripts/eval/kernels_rq8.py src/results/sqlite_kernels src/results/duckdb_kernels
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

METRICS = ("rule_pairs", "rules_fired", "plan_shapes", "testcases", "valid_query_rate", "bug_candidates",
           "pairs_per_1k_testcases")


def value(t: dict, m: str) -> float:
    if m == "pairs_per_1k_testcases":       # throughput-neutral: pairs reached per 1000 test cases
        return 1000.0 * float(t.get("rule_pairs") or 0) / max(1.0, float(t.get("testcases") or 0))
    return float(t.get(m) or 0)


def a12(xs: list[float], ys: list[float]) -> float:
    """Probability that a value from xs is larger than one from ys (ties count half)."""
    gt = sum(1.0 if x > y else 0.5 if x == y else 0.0 for x in xs for y in ys)
    return gt / (len(xs) * len(ys)) if xs and ys else float("nan")


def mwu_p(xs: list[float], ys: list[float]) -> float:
    try:
        from scipy.stats import mannwhitneyu

        return float(mannwhitneyu(xs, ys, alternative="two-sided").pvalue)
    except Exception:
        return float("nan")


def arms(exp: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for f in sorted(exp.glob("*/trial-*/summary.json")):
        out.setdefault(f.parent.parent.name, []).append(json.loads(f.read_text(encoding="utf-8")))
    return out


def main(paths: list[str]) -> int:
    for p in map(Path, paths):
        a = arms(p)
        base, kern = a.get("grammar_mm", []), a.get("grammar_kernels", [])
        print(f"\n### {p.name} ({len(base)} + {len(kern)} trials)\n")
        print("| metric | plain grammar (median) | + kernels (median) | A12 (kernels > plain) | p (MWU) |")
        print("|---|---|---|---|---|")
        for m in METRICS:
            xs = [value(t, m) for t in kern]
            ys = [value(t, m) for t in base]
            if not xs or not ys:
                continue
            fmt = (lambda v: f"{v:.3f}") if m in ("valid_query_rate",) else \
                (lambda v: f"{v:.1f}") if m == "pairs_per_1k_testcases" else (lambda v: f"{v:.0f}")
            print(f"| {m} | {fmt(statistics.median(ys))} | {fmt(statistics.median(xs))} | "
                  f"{a12(xs, ys):.2f} | {mwu_p(xs, ys):.3f} |")
        seen = {arm: set().union(*(set(t.get("rules_fired_counts", {})) for t in ts)) for arm, ts in a.items()}
        if "grammar_mm" in seen and "grammar_kernels" in seen:
            only = sorted(seen["grammar_kernels"] - seen["grammar_mm"])
            print(f"\nRules fired only with kernels (union over trials): {only or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
