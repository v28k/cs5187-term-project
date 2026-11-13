"""Generate the result tables of the paper from the raw campaign data in runs/ and triage/.

    python3 paper/scripts/make_tables.py          (from the repository root)

Writes paper/tables/rq1.tex, rq2.tex, rq3.tex, rq4.tex and copies the plots to paper/figures/.
Nothing is typed by hand: re-running after new data regenerates every number.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pgfuzz.eval.stats import a12, mann_whitney_u  # noqa: E402
from pgfuzz.triage.precision import load_verdicts, precision_table  # noqa: E402

RQ1 = ROOT / "runs/memberB-rq1-llm"
RQ3 = ROOT / "runs/memberA-rq3"
OUT = ROOT / "paper/tables"
FIG = ROOT / "paper/figures"

ARMS = [("random", "Random"), ("grammar", "Grammar"), ("grammar_mm", "Grammar+Oracles"),
        ("grammar_mm_flat", "Grammar+Oracles, flat"), ("llm_frag", "+LLM fragments"),
        ("llm_seeds", "+LLM seeds"), ("grammar_llm", "+LLM (both)")]


def fmt_int(x: float) -> str:
    return f"{round(x):,}".replace(",", "{,}")


def trials(path: Path) -> dict[str, dict[str, list[float]]]:
    d: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open(path / "report/trials.csv")):
        for k, v in r.items():
            if v not in ("", None):
                try:
                    d[r["config"]][k].append(float(v))
                except ValueError:
                    pass
    return d


def rq1() -> str:
    d = trials(RQ1)
    med = lambda a, k: statistics.median(d[a][k])           # noqa: E731
    rows = []
    for a, name in ARMS:
        rows.append(f"    \\arm{{{name}}} & {100 * med(a, 'valid_query_rate'):.1f} & {100 * med(a, 'line_coverage'):.1f} & "
                    f"{100 * med(a, 'branch_coverage'):.1f} & {fmt_int(med(a, 'features'))} & "
                    f"{fmt_int(med(a, 'plan_shapes'))} & {fmt_int(med(a, 'testcases'))} \\\\")
    return ("\\begin{tabular}{lrrrrrr}\n    \\toprule\n"
            "    Arm & Valid (\\%) & Lines (\\%) & Branches (\\%) & Features & Plan shapes & Test cases \\\\\n    \\midrule\n"
            + "\n".join(rows) + "\n    \\bottomrule\n  \\end{tabular}")


def rq1_effects() -> dict[str, str]:
    """Named effect sizes quoted in the text (so the text and the table cannot drift)."""
    d = trials(RQ1)
    out = {}

    def cmp(a: str, b: str, k: str, key: str) -> None:
        u = mann_whitney_u(d[a][k], d[b][k])
        out[key] = f"{statistics.median(d[a][k]):.4g}->{statistics.median(d[b][k]):.4g} p={u.p:.3f} A12={a12(d[b][k], d[a][k]):.2f}"

    cmp("random", "grammar", "line_coverage", "random_vs_grammar_lines")
    cmp("grammar", "grammar_mm", "line_coverage", "grammar_vs_mm_lines")
    cmp("grammar", "grammar_mm", "plan_shapes", "grammar_vs_mm_plans")
    cmp("grammar_mm_flat", "grammar_mm", "plan_shapes", "flat_vs_mm_plans")
    cmp("grammar_mm", "grammar_llm", "line_coverage", "mm_vs_llm_lines")
    cmp("grammar_mm", "grammar_llm", "features", "mm_vs_llm_features")
    cmp("grammar_mm", "llm_frag", "features", "mm_vs_frag_features")
    cmp("grammar_mm", "llm_seeds", "features", "mm_vs_seeds_features")
    return out


def rq3() -> str:
    att = json.load(open(RQ3 / "attribution.json"))["table"]["bugs"]
    keys = [a for a, _ in ARMS if a in att[0]]
    names = dict(ARMS)

    def cell(c: dict) -> str:
        return "0/5" if not c["found"] else f"{c['found']}/5 ({c['median_t']:.0f}\\,s)" if c["median_t"] else f"{c['found']}/5"

    found = [b for b in att if any(b[k]["found"] for k in keys)]
    rows = [f"    \\texttt{{{b['id'].replace('rb-', '')}}} & {b['symptom'].replace('_', ' ')} & "
            + " & ".join(cell(b[k]) for k in keys) + " \\\\" for b in found]
    by = defaultdict(list)
    for b in att:
        by[b["symptom"]].append(b)
    rows.append("    \\midrule")
    for sym in ("wrong_result", "internal_error", "assertion", "missing_error", "error"):
        if sym in by:
            tot = [sum(1 for b in by[sym] if b[k]["found"]) for k in keys]
            label = {"error": "wrong error"}.get(sym, sym.replace("_", " "))
            rows.append(f"    \\multicolumn{{2}}{{l}}{{{label}, {len(by[sym])} bug{'s' if len(by[sym]) != 1 else ''}: found}} & "
                        + " & ".join(f"{t}" for t in tot) + " \\\\")
    rows.append("    \\midrule")
    rows.append("    \\multicolumn{2}{l}{Bugs found (of 20)} & " + " & ".join(
        str(sum(1 for b in att if b[k]["found"])) for k in keys) + " \\\\")
    head = " & ".join(f"\\arm{{{names[k]}}}" for k in keys)
    return (f"\\begin{{tabular}}{{ll{'r' * len(keys)}}}\n    \\toprule\n    Bug & Symptom & {head} \\\\\n    \\midrule\n"
            + "\n".join(rows) + "\n    \\bottomrule\n  \\end{tabular}")


def rq2() -> str:
    rows = precision_table(load_verdicts(ROOT / "triage/verdicts.yaml"))
    out = []
    for r in rows:
        name = r["oracle"].replace("_", "\\_").replace("metamorphic:", "mm: ")
        if r["oracle"] == "all":
            out.append("    \\midrule")
        out.append(f"    {name} & {r['candidates']} & {r['real']} & {r['duplicate']} & "
                   f"{r['false_positive'] + r['not_a_bug']} & {r['flaky']} & {r['TODO']} \\\\")
    return ("\\begin{tabular}{lrrrrrr}\n    \\toprule\n"
            "    Oracle & Candidates & Real & Duplicate & False pos. & Flaky & Open \\\\\n    \\midrule\n"
            + "\n".join(out) + "\n    \\bottomrule\n  \\end{tabular}")


def rq4() -> str:
    text = (RQ1 / "logs/B2_llm_report.txt").read_text()
    kv = dict(re.findall(r"^\| (\w+) \| (.*?) \|$", text, re.M))
    tok = json.loads(kv["tokens"])
    rej = json.loads(kv["rejections_by_stage"])
    acc = json.loads(kv["accepted_by_round"])
    rows = [("Commits proposed for", kv["commits"]),
            ("Accepted by the gate", f"{kv['accepted']} ({100 * float(kv['acceptance_rate']):.0f}\\%): "
             f"{acc.get('1', 0)} in round 1, {acc.get('2', 0)} in round 2, {acc.get('3', 0)} in round 3"),
            ("Rounds in total", kv["rounds_total"]),
            ("Rejected rounds by stage", ", ".join(f"{k} {v}" for k, v in sorted(rej.items(), key=lambda kv_: -kv_[1]))),
            ("Mean validity of a proposal", f"{100 * float(kv['mean_validity']):.1f}\\%"),
            ("Diff-coverage gain", f"{kv['coverage_gain_lines']} changed lines"),
            ("Equivalence rewrites accepted", f"{kv['rewrites_accepted']} of {kv['rewrites_proposed']}"),
            ("Tokens (input / output / cached)", f"{fmt_int(tok['input_tokens'])} / {fmt_int(tok['output_tokens'])} / "
             f"{fmt_int(tok['cache_read_input_tokens'])}"),
            ("Cost", "0 USD (free tier)")]
    return ("\\begin{tabular}{p{0.4\\linewidth}p{0.5\\linewidth}}\n    \\toprule\n    Measure & Value \\\\\n    \\midrule\n"
            + "\n".join(f"    {a} & {b} \\\\" for a, b in rows) + "\n    \\bottomrule\n  \\end{tabular}")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    for name, fn in (("rq1", rq1), ("rq2", rq2), ("rq3", rq3), ("rq4", rq4)):
        (OUT / f"{name}.tex").write_text(fn() + "\n", encoding="utf-8")
        print("wrote", OUT / f"{name}.tex")
    for src, dst in (("timeline_line_coverage.png", "rq1_lines.png"), ("timeline_plan_shapes.png", "rq1_plans.png")):
        shutil.copy(RQ1 / "report" / src, FIG / dst)
    print(json.dumps(rq1_effects(), indent=1))


if __name__ == "__main__":
    main()
