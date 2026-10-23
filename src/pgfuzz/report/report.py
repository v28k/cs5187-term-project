"""Builds the evaluation report of an experiment from its run logs.

Outputs (in ``<experiment>/report/`` unless another directory is given):

* ``report.md``        human-readable summary: per-config medians, pairwise tests, bug table
* ``trials.csv``       one row per trial with every scalar metric
* ``comparison.csv``   pairwise Mann-Whitney U / A12 for every metric
* ``bugs.csv``         every unique bug-candidate signature and which configs found it
* ``table_*.tex``      LaTeX tables in the paper's style (booktabs, caption above)
* ``*.png``            metric-over-time plots (median with min-max band), if matplotlib is installed
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pgfuzz.eval import stats
from pgfuzz.runlog.reader import TrialData, load_experiment


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    higher_is_better: bool = True
    kind: str = "count"  # count | rate | float | seconds
    get: Callable[[dict[str, Any]], float | None] | None = None

    def value(self, summary: dict[str, Any]) -> float | None:
        v = self.get(summary) if self.get else summary.get(self.key)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        return float(v)


METRICS: list[Metric] = [
    Metric("line_coverage", "Line coverage", kind="rate"),
    Metric("branch_coverage", "Branch coverage", kind="rate"),
    Metric("edges", "Covered edges"),
    Metric("features", "SQL features"),
    Metric("feature_coverage", "SQL feature coverage", kind="rate"),
    Metric("feature_pairs", "Feature pairs"),
    Metric("query_shapes", "Distinct query shapes"),
    Metric("plan_shapes", "Distinct plan shapes", get=lambda s: s.get("plan_shapes") or None),
    Metric("mm_checks", "Metamorphic checks run", get=lambda s: (s.get("executor_stats") or {}).get("mm_checks")),
    Metric("variant_runs", "Plan-variant runs", get=lambda s: (s.get("executor_stats") or {}).get("variant_runs")),
    Metric("parse_valid_rate", "Parse-valid rate", kind="rate"),
    Metric("valid_query_rate", "Valid-query rate", kind="rate"),
    Metric("statements_per_s", "Statements/s", kind="float"),
    Metric("testcases", "Test cases"),
    Metric("bug_candidates", "Unique bug candidates"),
    Metric("known_bugs", "Known bugs reproduced", get=lambda s: len(s.get("known_bugs_reproduced") or [])),
    Metric("time_to_first_bug_s", "Time to first bug (s)", higher_is_better=False, kind="seconds"),
]

TIMELINE_SERIES = [
    ("features", "SQL features covered", lambda r: r.get("features")),
    ("feature_pairs", "Feature pairs covered", lambda r: r.get("feature_pairs")),
    ("bug_candidates", "Unique bug candidates", lambda r: r.get("bug_candidates")),
    ("plan_shapes", "Distinct plan shapes", lambda r: r.get("plan_shapes") or None),
    ("valid_rate", "Cumulative valid-query rate", lambda r: (r["valid"] / r["statements"]) if r.get("statements") else None),
    ("line_coverage", "Lines covered", lambda r: (r.get("coverage") or {}).get("lines_covered")),
    ("branch_coverage", "Branches covered", lambda r: (r.get("coverage") or {}).get("branches_covered")),
    ("edges", "Edges covered", lambda r: (r.get("coverage") or {}).get("edges")),
]


# --------------------------------------------------------------------------- formatting

def fmt(v: float | None, kind: str, latex: bool = False) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "--" if latex else "-"
    if kind == "rate":
        return f"{100 * v:.1f}\\%" if latex else f"{100 * v:.1f}%"
    if kind in ("float", "seconds"):
        s = f"{v:,.1f}"
    else:
        s = f"{v:,.0f}" if abs(v - round(v)) < 1e-9 else f"{v:,.1f}"
    return s.replace(",", "{,}") if latex else s


def fmt_p(p: float) -> str:
    if math.isnan(p):
        return "-"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def tex_escape(s: str) -> str:
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")):
        s = s.replace(a, b)
    return s


# --------------------------------------------------------------------------- analysis

def _values(trials: list[TrialData], m: Metric) -> list[float]:
    return [v for t in trials if (v := m.value(t.summary)) is not None]


def _active_metrics(groups: dict[str, list[TrialData]]) -> list[Metric]:
    return [m for m in METRICS if any(_values(ts, m) for ts in groups.values())]


def _pairs(order: list[str], baseline: str | None) -> list[tuple[str, str]]:
    """Consecutive pairs (Random->Grammar, Grammar->Grammar+LLM) plus each arm vs baseline."""
    pairs = list(zip(order, order[1:]))
    if baseline in order:
        pairs += [(baseline, c) for c in order if c != baseline and (baseline, c) not in pairs]
    return pairs


def compare(groups: dict[str, list[TrialData]], order: list[str], baseline: str | None) -> list[dict[str, Any]]:
    rows = []
    for a, b in _pairs(order, baseline):
        for m in _active_metrics(groups):
            xa, xb = _values(groups[a], m), _values(groups[b], m)
            if not xa or not xb:
                continue
            mw = stats.mann_whitney_u(xb, xa)
            eff = stats.a12(xb, xa)
            if not m.higher_is_better:
                eff = 1 - eff
            rows.append({
                "metric": m.key, "label": m.label, "a": a, "b": b,
                "median_a": stats.median(xa), "median_b": stats.median(xb),
                "n_a": len(xa), "n_b": len(xb),
                "p": mw.p, "test": mw.method, "a12_b_better": eff, "effect": stats.a12_magnitude(eff),
            })
    return rows


def bug_table(groups: dict[str, list[TrialData]]) -> list[dict[str, Any]]:
    bugs: dict[str, dict[str, Any]] = {}
    for name, trials in groups.items():
        for t in trials:
            for s in t.summary.get("signatures") or []:
                b = bugs.setdefault(s["id"], {
                    "signature": s["id"], "outcome": s["outcome"], "strength": s["strength"],
                    "sqlstate": s.get("sqlstate"), "message": (s.get("message") or s["key"])[:160],
                    "known_bugs": ",".join(s.get("known_bugs") or []), "found_by": {}, "first_t": {},
                    "example": str(t.path / "failures" / s["id"] / "testcase.sql"),
                })
                b["found_by"][name] = b["found_by"].get(name, 0) + 1
                b["first_t"][name] = min(b["first_t"].get(name, math.inf), s["first_t"])
    return sorted(bugs.values(), key=lambda b: (-sum(b["found_by"].values()), b["signature"]))


# --------------------------------------------------------------------------- outputs

def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})


def _trial_rows(groups: dict[str, list[TrialData]]) -> list[dict[str, Any]]:
    rows = []
    for name, trials in groups.items():
        for t in trials:
            s = t.summary
            row = {"config": name, "trial": t.trial, "seed": s.get("seed"), "stop_reason": s.get("stop_reason"),
                   "elapsed_s": s.get("elapsed_s")}
            for m in METRICS:
                row[m.key] = m.value(s)
            row["harness_errors"] = s.get("harness_errors")
            rows.append(row)
    return rows


def _latex_summary(groups: dict[str, list[TrialData]], order: list[str], labels: dict[str, str], exp: str) -> str:
    ms = _active_metrics(groups)
    n = {c: len(groups[c]) for c in order}
    cols = "l" + "r" * len(order)
    head = " & ".join(["Metric"] + [tex_escape(labels[c]) for c in order])
    lines = [
        r"\begin{table}[t]",
        r"  \caption{Median over " + ("/".join(str(n[c]) for c in order) if len(set(n.values())) > 1 else str(next(iter(n.values()), 0)))
        + r" trials per configuration (experiment \texttt{" + tex_escape(exp) + r"}). Rates are shares of executed statements; "
        r"coverage is measured on the instrumented server; bug candidates are unique failure signatures.}",
        r"  \label{tab:" + exp.replace("_", "-") + r"-summary}",
        r"  \footnotesize",
        r"  \begin{tabular}{" + cols + "}",
        r"    \toprule",
        f"    {head} \\\\",
        r"    \midrule",
    ]
    for m in ms:
        cells = [fmt(stats.median(v) if (v := _values(groups[c], m)) else None, m.kind, latex=True) for c in order]
        lines.append(f"    {tex_escape(m.label)} & " + " & ".join(cells) + r" \\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def _latex_comparison(rows: list[dict[str, Any]], labels: dict[str, str], exp: str) -> str:
    lines = [
        r"\begin{table}[t]",
        r"  \caption{Pairwise comparison per metric. \emph{p}: two-sided Mann-Whitney U test; "
        r"\emph{$\hat{A}_{12}$}: Vargha-Delaney effect size, probability that the second configuration is better "
        r"(0.5 = no difference).}",
        r"  \label{tab:" + exp.replace("_", "-") + r"-comparison}",
        r"  \footnotesize",
        r"  \begin{tabular}{llrrrr}",
        r"    \toprule",
        r"    Comparison & Metric & Median A & Median B & \emph{p} & $\hat{A}_{12}$ \\",
        r"    \midrule",
    ]
    kinds = {m.key: m.kind for m in METRICS}
    for r in rows:
        k = kinds.get(r["metric"], "float")
        comp = tex_escape(f"{labels.get(r['a'], r['a'])} vs {labels.get(r['b'], r['b'])}")
        lines.append(
            f"    {comp} & {tex_escape(r['label'])} & {fmt(r['median_a'], k, True)} & {fmt(r['median_b'], k, True)} & "
            f"{tex_escape(fmt_p(r['p']))} & {r['a12_b_better']:.2f} \\\\"
        )
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def _markdown(groups, order, labels, comp, bugs, exp, incomplete) -> str:
    ms = _active_metrics(groups)
    out = [f"# Evaluation report: `{exp}`", ""]
    out.append("Trials per configuration: " + ", ".join(f"{labels[c]} = {len(groups[c])}" for c in order))
    budgets = {json.dumps(t.manifest.get("budget"), sort_keys=True) for ts in groups.values() for t in ts}
    out.append(f"Budget per trial: {', '.join(sorted(budgets))}")
    stops = sorted({t.summary.get("stop_reason") for ts in groups.values() for t in ts})
    out.append(f"Stop reasons: {', '.join(map(str, stops))}")
    if incomplete:
        out += ["", f"**Warning:** {len(incomplete)} trial(s) did not finish normally and are excluded: "
                + ", ".join(incomplete)]
    mock = sorted({t.manifest.get("executor", {}).get("plugin", "") for ts in groups.values() for t in ts if "mock" in t.manifest.get("executor", {}).get("plugin", "").lower()})
    if mock:
        out += ["", "**Warning:** these trials used a mock executor. Their numbers test the pipeline only "
                "and must not appear in the paper."]

    out += ["", "## Median (IQR) per configuration", ""]
    out.append("| Metric | " + " | ".join(labels[c] for c in order) + " |")
    out.append("|---|" + "---:|" * len(order))
    for m in ms:
        cells = []
        for c in order:
            v = _values(groups[c], m)
            if v:
                lo, hi = stats.iqr(v)
                cells.append(f"{fmt(stats.median(v), m.kind)} ({fmt(lo, m.kind)}-{fmt(hi, m.kind)})")
            else:
                cells.append("-")
        out.append(f"| {m.label} | " + " | ".join(cells) + " |")

    if comp:
        out += ["", "## Pairwise comparisons", "",
                "`A12` is the probability that B beats A on that metric (0.5 = no difference; "
                "lower-is-better metrics are flipped). `p` is from a two-sided Mann-Whitney U test.", "",
                "| A | B | Metric | Median A | Median B | p | A12 | Effect |", "|---|---|---|---:|---:|---:|---:|---|"]
        kinds = {m.key: m.kind for m in METRICS}
        for r in comp:
            k = kinds.get(r["metric"], "float")
            out.append(f"| {labels.get(r['a'], r['a'])} | {labels.get(r['b'], r['b'])} | {r['label']} | "
                       f"{fmt(r['median_a'], k)} | {fmt(r['median_b'], k)} | {fmt_p(r['p'])} | "
                       f"{r['a12_b_better']:.2f} | {r['effect']} |")

    out += ["", "## Unique bug candidates", ""]
    if not bugs:
        out.append("None found.")
    else:
        out.append("| Signature | Outcome | Strength | SQLSTATE | Message | Found by (trials) | Known bug |")
        out.append("|---|---|---|---|---|---|---|")
        for b in bugs:
            found = ", ".join(f"{labels.get(k, k)} ({v})" for k, v in b["found_by"].items())
            msg = (b["message"] or "").replace("|", "\\|")
            out.append(f"| `{b['signature']}` | {b['outcome']} | {b['strength']} | {b['sqlstate'] or '-'} | "
                       f"{msg} | {found} | {b['known_bugs'] or '-'} |")
        out += ["", "Each signature has a replayable `testcase.sql` under "
                "`<config>/trial-NN/failures/<signature>/`. Validate on a fresh server before reporting."]
    return "\n".join(out) + "\n"


def _plot(groups, order, labels, out: Path) -> list[Path]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    written = []
    for key, title, get in TIMELINE_SERIES:
        series = {}
        for c in order:
            runs = []
            for t in groups[c]:
                pts = [(r["t"], v) for r in t.timeline if (v := get(r)) is not None]
                if pts:
                    runs.append(pts)
            if runs:
                series[c] = runs
        if not series:
            continue
        horizon = max(p[-1][0] for runs in series.values() for p in runs)
        if horizon <= 0:
            continue
        grid = [horizon * i / 200 for i in range(201)]
        fig, ax = plt.subplots(figsize=(5.5, 3.2))
        for c, runs in series.items():
            cols = [[_step(r, g) for r in runs] for g in grid]
            med = [stats.median([v for v in col if v is not None]) if any(v is not None for v in col) else math.nan for col in cols]
            lo = [min((v for v in col if v is not None), default=math.nan) for col in cols]
            hi = [max((v for v in col if v is not None), default=math.nan) for col in cols]
            line, = ax.plot(grid, med, label=f"{labels[c]} (n={len(runs)})")
            ax.fill_between(grid, lo, hi, alpha=0.2, color=line.get_color(), linewidth=0)
        ax.set_xlabel("time (s)")
        ax.set_ylabel(title)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        p = out / f"timeline_{key}.png"
        fig.savefig(p, dpi=150)
        plt.close(fig)
        written.append(p)
    return written


def _step(points: list[tuple[float, float]], t: float) -> float | None:
    """Value of a step series at time t (last observation carried forward)."""
    v = None
    for pt, pv in points:
        if pt > t:
            break
        v = pv
    return v


def _rq3_cells(row: dict[str, Any], arm: str) -> tuple[int, int, float | None]:
    c = row.get(arm) or {"found": 0, "trials": 0, "median_t": None}
    return c["found"], c["trials"], c["median_t"]


def _rq3_markdown(table: dict[str, Any], order: list[str], labels: dict[str, str]) -> str:
    arms = [a for a in order if a in table["found_by_arm"]]
    out = ["", "## Re-injected bugs (RQ3)", "",
           "Trials in which the arm found the bug, and the median time to the first finding "
           "(failures attributed by replay on single-bug servers, `pgfuzz bench attribute`).", "",
           "| Bug | Symptom | " + " | ".join(labels.get(a, a) for a in arms) + " |",
           "|---|---|" + "---:|" * len(arms)]
    for r in table["bugs"]:
        cells = []
        for a in arms:
            n, k, t = _rq3_cells(r, a)
            cells.append(f"{n}/{k}" + (f" ({t:.0f} s)" if t is not None else ""))
        out.append(f"| {r['id']} | {r['symptom']} | " + " | ".join(cells) + " |")
    out.append("| **bugs found** | | " + " | ".join(
        f"**{table['found_by_arm'][a]}/{table['observable_bugs']}**" for a in arms) + " |")
    out += ["", f"Failures that also reproduce on the fixed server (native): {table['native_failures']}; "
            f"not attributable to one injected bug: {table['unattributed_failures']}.", ""]
    return "\n".join(out)


def _rq3_latex(table: dict[str, Any], order: list[str], labels: dict[str, str], exp: str) -> str:
    arms = [a for a in order if a in table["found_by_arm"]]
    lines = [r"\begin{table}[t]", r"  \centering", r"  \small",
             rf"  \caption{{Re-injected bugs found per arm: trials with a finding and median time to the first "
             rf"finding in seconds (experiment \texttt{{{tex_escape(exp)}}}).}}",
             r"  \label{tab:rq3}", r"  \begin{tabular}{ll" + "r" * len(arms) + "}", r"    \toprule",
             "    Bug & Symptom & " + " & ".join(tex_escape(labels.get(a, a)) for a in arms) + r" \\", r"    \midrule"]
    for r in table["bugs"]:
        cells = []
        for a in arms:
            n, k, t = _rq3_cells(r, a)
            cells.append(f"{n}/{k}" + (f" ({t:.0f})" if t is not None else ""))
        lines.append(f"    \\texttt{{{tex_escape(r['id'])}}} & {tex_escape(r['symptom'])} & " + " & ".join(cells) + r" \\")
    lines += [r"    \midrule", "    Bugs found & & " + " & ".join(
        f"{table['found_by_arm'][a]}/{table['observable_bugs']}" for a in arms) + r" \\",
              r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def build_report(experiment_dir: str | Path, out_dir: str | Path | None = None, plots: bool = True) -> Path:
    exp_dir = Path(experiment_dir)
    groups_all = load_experiment(exp_dir)
    if not groups_all:
        raise FileNotFoundError(f"no finished trials under {exp_dir}")

    meta_path = exp_dir / "experiment.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    declared = [c["name"] for c in meta.get("configs", [])]
    labels = {c["name"]: c["label"] for c in meta.get("configs", [])}

    incomplete = []
    groups: dict[str, list[TrialData]] = {}
    for name, trials in groups_all.items():
        for t in trials:
            if t.summary.get("stop_reason") in ("interrupted", "error"):
                incomplete.append(f"{name}/trial-{t.trial:02d}")
            else:
                groups.setdefault(name, []).append(t)
            labels.setdefault(name, t.manifest.get("label") or name)
    order = [c for c in declared if c in groups] + sorted(c for c in groups if c not in declared)
    exp = meta.get("experiment") or exp_dir.name

    out = Path(out_dir) if out_dir else exp_dir / "report"
    out.mkdir(parents=True, exist_ok=True)

    comp = compare(groups, order, meta.get("baseline"))
    bugs = bug_table(groups)
    _write_csv(out / "trials.csv", _trial_rows(groups))
    _write_csv(out / "comparison.csv", comp)
    _write_csv(out / "bugs.csv", [{**b, "found_by": b["found_by"], "first_t": b["first_t"]} for b in bugs])
    (out / "table_summary.tex").write_text(_latex_summary(groups, order, labels, exp), encoding="utf-8")
    if comp:
        (out / "table_comparison.tex").write_text(_latex_comparison(comp, labels, exp), encoding="utf-8")
    md = _markdown(groups, order, labels, comp, bugs, exp, incomplete)
    att = exp_dir / "attribution.json"
    if att.exists():                     # RQ3: written by `pgfuzz bench attribute`
        table = json.loads(att.read_text(encoding="utf-8"))["table"]
        md += _rq3_markdown(table, order, labels)
        (out / "table_rq3.tex").write_text(_rq3_latex(table, order, labels, exp), encoding="utf-8")
    (out / "report.md").write_text(md, encoding="utf-8")
    if plots:
        _plot(groups, order, labels, out)
    return out
