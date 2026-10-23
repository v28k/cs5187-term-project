"""RQ3 benchmark: real PostgreSQL bugs re-injected by reverting their fixes.

``bench/reinjected/bugs.yaml`` lists each bug (fix commit, PoC, observed symptom)
and doubles as the known-bug catalog of ``configs/rq3.yaml``: crash, assertion
and error bugs have a signature the campaign matches online; wrong-result bugs
are marked ``offline`` and are attributed after the campaign (a plan-variant or
metamorphic mismatch does not say which bug caused it).

Servers (``scripts/rq3_servers.sh``): ``fixed`` = base, ``solo[i]`` = base with
only bug i re-injected, ``injected`` = base with all of them.

``verify``    runs every PoC on fixed, solo and injected and derives the symptom
              from the difference: a PoC that behaves the same on fixed and solo
              shows no symptom our oracles could see (e.g. a plan-quality fix),
              and that bug is excluded from the RQ3 denominator.
``attribute`` replays every failure of a campaign on fixed and on each solo
              server: a failure that reproduces on solo[i] but not on fixed is
              attributed to bug i; one that reproduces on fixed is native (a
              bug of the base, or a false positive).
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pgfuzz.core.sqlsplit import split_statements
from pgfuzz.core.types import Outcome, TestCase
from pgfuzz.eval import oracle
from pgfuzz.triage.triage import Runner, load_candidate

SOLO_BASE, FIXED_WORKER = 21, 20


@dataclass
class Bug:
    id: str
    commit: str
    title: str
    poc: Path
    symptom: str = "unknown"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Bench:
    path: Path
    base: str
    bugs: list[Bug]

    def solo_worker(self, i: int) -> int:
        return SOLO_BASE + i


def load(path: str | Path) -> Bench:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    order = [ln.split()[0] for ln in (path.parent / "commits.txt").read_text().splitlines()
             if ln.strip() and not ln.startswith("#")]
    by_commit = {str(e.get("commit", ""))[:8]: e for e in data.get("bugs") or []}
    bugs = []
    for c in order:            # solo worker numbers follow commits.txt, so keep its order
        e = by_commit.get(c[:8], {"id": f"rb-{c[:8]}", "commit": c, "title": ""})
        bugs.append(Bug(e["id"], str(e["commit"]), e.get("title", ""), path.parent / "pocs" / f"{c[:8]}.sql",
                        e.get("symptom", "unknown"), e))
    return Bench(path, str(data.get("base", "")), bugs)


# ------------------------------------------------------------------ verify
def observe(ex: Any, sql: str) -> dict[str, Any]:
    stmts = split_statements(sql)
    res = ex.execute(TestCase(stmts, origin="bench"))
    cls = oracle.classify(res)
    return {"outcome": cls.outcome.value, "message": cls.message, "details": _small(cls.details),
            "statements": [{"status": r.status.value, "sqlstate": r.sqlstate, "message": r.message,
                            "rows": r.rows, "hash": r.result_hash} for r in res.statements]}


def _small(d: dict[str, Any]) -> dict[str, Any]:
    return {k: d[k] for k in ("assertion", "panic", "signal") if k in d}


def symptom(fixed: dict[str, Any], buggy: dict[str, Any]) -> tuple[str, str]:
    """(symptom, evidence) of ``buggy`` relative to ``fixed`` for the same PoC."""
    if buggy["outcome"] in ("crash", "assertion", "panic"):
        a = buggy["details"].get("assertion")
        return buggy["outcome"], f"{a['file']}: {a['expr']}" if a else (buggy["message"] or "")
    for i, (f, b) in enumerate(zip(fixed["statements"], buggy["statements"])):
        if f["status"] == "ok" and b["status"] != "ok":
            kind = "internal_error" if (b["sqlstate"] or "").startswith("XX") else "error"
            return kind, f"stmt {i}: {b['sqlstate']} {b['message']}"
        if f["status"] != "ok" and b["status"] == "ok":
            return "missing_error", f"stmt {i}: fixed raises {f['sqlstate']} {f['message']}"
        if f["status"] == b["status"] == "ok" and (f["hash"] != b["hash"] or f["rows"] != b["rows"]):
            return "wrong_result", f"stmt {i}: {f['rows']} rows on fixed, {b['rows']} on buggy"
        if f["status"] == b["status"] != "ok" and f["message"] != b["message"]:
            return "error", f"stmt {i}: different error: {b['sqlstate']} {b['message']}"
    return "none", ""


def verify(bench: Bench, fixed: Any, solos: list[Any], injected: Any | None) -> list[dict[str, Any]]:
    rows = []
    for bug, solo in zip(bench.bugs, solos):
        sql = bug.poc.read_text(encoding="utf-8")
        f = observe(fixed, sql)
        s = observe(solo, sql)
        sym, ev = symptom(f, s)
        row = {"id": bug.id, "commit": bug.commit, "title": bug.title, "symptom": sym, "evidence": ev,
               "fixed_outcome": f["outcome"], "solo_outcome": s["outcome"],
               # a PoC whose setup fails on the fixed server tests nothing: surface it
               "fixed_errors": [f"stmt {j}: {st['sqlstate']} {st['message']}" for j, st in enumerate(f["statements"])
                                if st["status"] != "ok"]}
        if injected is not None:
            i = observe(injected, sql)
            row["injected_symptom"], _ = symptom(f, i)
        rows.append(row)
    return rows


# ------------------------------------------------------------------ attribute
def failures(exp_dir: str | Path) -> list[dict[str, Any]]:
    """Every saved failure of a campaign: arm, trial, path, first time."""
    out = []
    for fj in sorted(Path(exp_dir).glob("*/trial-*/failures/*/failure.json")):
        info = json.loads(fj.read_text(encoding="utf-8"))
        trial_dir = fj.parent.parent.parent
        out.append({"arm": trial_dir.parent.name, "trial": trial_dir.name, "dir": fj.parent,
                    "signature": info.get("signature"), "outcome": info.get("outcome"),
                    "first_t": info.get("first_t"), "known_bugs": info.get("known_bugs") or []})
    return out


def _reproduces(ex: Any, cand: Any, repeat: int) -> bool:
    r = Runner(ex, cand)
    return any(r.reproduces(cand.statements, cand.culprit, cand.check) for _ in range(repeat))


def attribute(bench: Bench, exp_dir: str | Path, fixed: Any, solos: list[Any], repeat: int = 2,
              only_offline: bool = False) -> list[dict[str, Any]]:
    results = []
    offline = {b.id for b in bench.bugs if (b.raw.get("match") or {}).get("offline")}
    for f in failures(exp_dir):
        if only_offline and f["known_bugs"] and not set(f["known_bugs"]) & offline:
            results.append({**f, "dir": str(f["dir"]), "bugs": f["known_bugs"], "how": "signature"})
            continue
        cand = load_candidate(f["dir"])
        if _reproduces(fixed, cand, repeat):
            results.append({**f, "dir": str(f["dir"]), "bugs": [], "how": "native"})
            continue
        hit = [b.id for b, ex in zip(bench.bugs, solos) if _reproduces(ex, cand, repeat)]
        results.append({**f, "dir": str(f["dir"]), "bugs": hit, "how": "solo" if hit else "unattributed"})
    return results


def detection_table(bench: Bench, attributed: list[dict[str, Any]], arms: list[str], trials: int) -> dict[str, Any]:
    """Per bug and arm: trials that found it and the median time to the first finding."""
    first: dict[tuple[str, str], dict[str, float]] = {}
    for r in attributed:
        for b in r["bugs"]:
            d = first.setdefault((b, r["arm"]), {})
            t = r["first_t"] if r["first_t"] is not None else float("inf")
            d[r["trial"]] = min(d.get(r["trial"], float("inf")), t)
    table = []
    for bug in bench.bugs:
        if bug.symptom == "none":
            continue
        row: dict[str, Any] = {"id": bug.id, "symptom": bug.symptom}
        for arm in arms:
            ts = sorted(first.get((bug.id, arm), {}).values())
            row[arm] = {"found": len(ts), "trials": trials,
                        "median_t": round(statistics.median(ts), 1) if ts else None}
        table.append(row)
    totals = {arm: sum(1 for r in table if r[arm]["found"]) for arm in arms}
    return {"bugs": table, "found_by_arm": totals, "observable_bugs": len(table),
            "native_failures": sum(r["how"] == "native" for r in attributed),
            "unattributed_failures": sum(r["how"] == "unattributed" for r in attributed)}


def render_markdown(t: dict[str, Any], arms: list[str]) -> str:
    lines = ["| bug | symptom | " + " | ".join(arms) + " |", "|---|---|" + "---|" * len(arms)]
    for r in t["bugs"]:
        cells = []
        for a in arms:
            c = r[a]
            cells.append(f"{c['found']}/{c['trials']}" + (f" ({c['median_t']:.0f}s)" if c["median_t"] is not None else ""))
        lines.append(f"| {r['id']} | {r['symptom']} | " + " | ".join(cells) + " |")
    lines.append("| **bugs found** | | " + " | ".join(f"**{t['found_by_arm'][a]}/{t['observable_bugs']}**" for a in arms) + " |")
    return "\n".join(lines)
