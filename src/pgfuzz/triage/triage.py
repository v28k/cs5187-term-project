"""Triage one bug candidate: reproduce, reduce, compare with a release, write a report.

Input is a failure directory written by a campaign
(``results/<exp>/<config>/trial-NN/failures/<signature>/``: ``failure.json`` and
``testcase.sql``) or a candidate saved by ``pgfuzz sample --out`` (``tcN.json``
and ``tcN.sql``). Output, per candidate, in ``<out>/<signature>/``::

    reduced.sql      the reduced test case (setup statements, then the culprit;
                     for differential candidates the variant settings or the
                     metamorphic follow-up are written out explicitly)
    triage.json      reproduction counts, sizes, timings, verdict template
    report.md        a draft bug report (expected vs actual, versions, backtrace)

Every reduction step re-executes the candidate through the same executor and
oracle as the campaign and keeps it only if the *same* failure reproduces
(:func:`same_failure`), so the reduced case is a real reproducer, not a guess.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pgfuzz.core.sqlsplit import split_statements
from pgfuzz.core.types import Outcome, TestCase
from pgfuzz.eval import oracle, signature
from pgfuzz.eval.oracle import Classification
from pgfuzz.triage.reduce import TokenReducer, fill, reduce_statements, split_pair
from pgfuzz.triage.sqltok import lex, render


@dataclass
class Candidate:
    source: Path
    statements: list[str]
    culprit: int
    outcome: Outcome
    details: dict[str, Any]
    sqlstate: str | None = None
    message: str | None = None
    signature: str = ""
    check: dict[str, Any] | None = None       # metamorphic follow-up of the culprit
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def oracle_name(self) -> str:
        """Which oracle reported it (the unit of the precision table)."""
        d = self.details
        if d.get("oracle") == "metamorphic":
            return "metamorphic:" + str(d.get("check", "?")).split(":")[0]
        if d.get("variant") == "xversion":
            return "cross-version"
        if d.get("variant"):
            return "plan-variant"
        return self.outcome.value      # crash / assertion / internal_error / ...


def load_candidate(path: str | Path) -> Candidate:
    p = Path(path)
    if p.is_dir():
        info = json.loads((p / "failure.json").read_text(encoding="utf-8"))
        sql_file = p / "testcase.sql"
    else:
        info = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
        sql_file = p.with_suffix(".sql")
    stmts = split_statements(sql_file.read_text(encoding="utf-8"))
    culprit = info.get("culprit")
    culprit = int(culprit) if culprit is not None else len(stmts) - 1
    details = info.get("details") or {}
    meta = info.get("meta") or {}
    check = None
    if details.get("oracle") == "metamorphic":
        for c in meta.get("checks") or []:
            if isinstance(c, dict) and c.get("stmt") == culprit and c.get("kind") == details.get("check"):
                check = dict(c)
                break
    return Candidate(p, stmts, culprit, Outcome(info["outcome"]), details, info.get("sqlstate"), info.get("message"),
                     info.get("signature") or p.stem, check, meta)


def same_failure(want: Candidate, got: Classification) -> bool:
    """Does ``got`` show the same failure as the candidate (not just any failure)?"""
    if got.outcome is not want.outcome:
        return False
    d, g = want.details, got.details
    if "assertion" in d:
        a, b = d["assertion"], g.get("assertion") or {}
        return a.get("file") == b.get("file") and a.get("expr") == b.get("expr")
    if want.outcome is Outcome.WRONG_RESULT:
        return d.get("variant") == g.get("variant")
    if want.outcome in (Outcome.INTERNAL_ERROR, Outcome.DATA_CORRUPTION):
        return signature.normalize_message(want.message) == signature.normalize_message(got.message)
    if want.outcome is Outcome.PANIC:
        return signature.normalize_message(d.get("panic")) == signature.normalize_message(g.get("panic"))
    return True   # crash without an assertion: any crash of the same statement


class Runner:
    """Executes candidate variants with the campaign's executor, configured for the
    candidate's oracle (only the failing plan variant, metamorphic checks on)."""

    def __init__(self, executor: Any, cand: Candidate) -> None:
        self.ex = executor
        self.cand = cand
        base = getattr(executor, "test", executor)   # CrossVersionExecutor wraps the test server
        self.base = base
        v = cand.details.get("variant")
        if cand.outcome is Outcome.WRONG_RESULT and v and v != "xversion" and not str(v).startswith("mm:"):
            base.diff_enabled = True
            base.variants = {v: dict(cand.details.get("settings") or {})}
            base.diff_per_query = 1
        if cand.check is not None:
            base.mm_enabled = True
            base.mm_confirm = True
        self.runs = 0

    def classify(self, statements: list[str], culprit: int, check: dict[str, Any] | None = None) -> Classification:
        self.runs += 1
        meta = {"checks": [dict(check, stmt=culprit)]} if check is not None else {}
        res = self.ex.execute(TestCase(statements, origin="triage", meta=meta))
        return oracle.classify(res)

    def reproduces(self, statements: list[str], culprit: int, check: dict[str, Any] | None = None) -> bool:
        return same_failure(self.cand, self.classify(statements, culprit, check))

    def rows(self, executor: Any, statements: list[str], query: str, limit: int = 30) -> dict[str, Any]:
        """Run setup statements and ``query`` in a rolled-back transaction; return text rows."""
        import psycopg

        ex = getattr(executor, "test", executor)
        if not ex._alive():
            ex._connect(wait=True)
        out: dict[str, Any] = {}
        try:
            ex.conn.execute("BEGIN")
            for s in statements:
                ex.conn.execute("SAVEPOINT t")
                try:
                    ex.conn.execute(s)
                    ex.conn.execute("RELEASE SAVEPOINT t")
                except psycopg.Error:
                    ex.conn.execute("ROLLBACK TO SAVEPOINT t")
            cur = ex.conn.execute(query)
            data = cur.fetchall() if cur.description is not None else []
            out = {"columns": [c.name for c in cur.description or []], "rows": [list(r) for r in data[:limit]],
                   "row_count": len(data)}
        except psycopg.Error as e:
            out = {"error": f"{getattr(e, 'sqlstate', '')} {e}".strip()}
        finally:
            try:
                if ex._alive():
                    ex.conn.execute("ROLLBACK")
            except psycopg.Error:
                pass
        return out


def triage(cand: Candidate, executor: Any, out_dir: Path, *, repeat: int = 3, reduce: bool = True,
           reference: Any = None, budget: int = 400, log: Callable[[str], None] = print,
           tree_gen: Any = None) -> dict[str, Any]:
    """``tree_gen``: a set-up GrammarGenerator for the candidate's grammar; when the
    candidate carries derivation trees, they are reduced on the tree first."""
    run = Runner(executor, cand)
    t0 = time.monotonic()
    stmts, culprit, check = list(cand.statements), cand.culprit, cand.check
    if check is not None and check.get("lhs") is not None:
        # TLP / NoREC: both sides are explicit queries; the culprit only anchors them.
        stmts[culprit] = "SELECT 1"

    log(f"[{cand.signature}] {cand.outcome.value} via {cand.oracle_name}: reproducing x{repeat}")
    hits = sum(run.reproduces(stmts, culprit, check) for _ in range(repeat))
    result: dict[str, Any] = {
        "signature": cand.signature, "source": str(cand.source), "outcome": cand.outcome.value,
        "oracle": cand.oracle_name, "reproduced": f"{hits}/{repeat}",
        "original": {"statements": len(cand.statements), "culprit_tokens": len(lex(cand.statements[cand.culprit]))},
    }
    if hits == 0:
        result["verdict"] = "flaky"
        log("  does not reproduce: marked flaky")
        _write(out_dir, cand, result, stmts, culprit, check, None, None)
        return result

    if reduce and tree_gen is not None and check is None:
        from pgfuzz.triage.tree_reduce import TreeReducer, load_trees

        trees = load_trees(cand.meta or {}, tree_gen)
        if trees:
            tr = TreeReducer(tree_gen, lambda sql: run.reproduces(sql, 0, None), budget=budget // 2, log=log)
            got = tr.reduce(trees)
            if got is not None:
                stmts = list(got[1])
                c = run.classify(stmts, 0).culprit
                culprit = c if c is not None else len(stmts) - 1
                result["tree_reduction"] = {"tokens_after": sum(len(lex(x)) for x in stmts), "runs": tr.runs,
                                            "replays": tr.derived}

    if reduce:
        stmts, culprit = reduce_statements(stmts, culprit, lambda s, k: run.reproduces(s, k, check), log=log)
        pair = None
        if check is not None and check.get("lhs") is None:
            pair = split_pair(stmts[culprit], str(check["rhs"]))
        if check is None or pair is not None:
            if pair is not None:
                skel, mid_a, mid_b = pair
            else:
                skel, mid_a, mid_b = lex(stmts[culprit]), [], []

            def interesting(cand_toks):
                a = render(fill(cand_toks, mid_a)) if pair else render(cand_toks)
                c = dict(check, rhs=render(fill(cand_toks, mid_b))) if pair else check
                s2 = stmts[:culprit] + [a] + stmts[culprit + 1:]
                return run.reproduces(s2, culprit, c)

            red = TokenReducer(interesting, budget=budget, log=log).reduce(skel)
            stmts[culprit] = render(fill(red, mid_a)) if pair else render(red)
            if pair:
                check = dict(check, rhs=render(fill(red, mid_b)))
        # confirm the final case once more
        if not run.reproduces(stmts, culprit, check):
            log("  WARNING: reduced case does not reproduce on the final check")
            result["reduced_reproduces"] = False

    result["reduced"] = {"statements": len(stmts), "culprit_tokens": len(lex(stmts[culprit]))}
    result["runs"] = run.runs
    result["seconds"] = round(time.monotonic() - t0, 1)

    # what each side returns, on the test server and (if given) on a release
    shown = _queries_to_show(cand, stmts, culprit, check)
    setup = stmts[:culprit]
    result["observed"] = {name: run.rows(executor, setup, q) for name, q in shown.items()}
    if reference is not None:
        ref_ex = getattr(reference, "ref", reference)
        result["observed_reference"] = {name: run.rows(ref_ex, setup, q) for name, q in shown.items()}
        result["reference_server"] = ref_ex.describe().get("server_version")
    result["test_server"] = run.base.describe().get("server_version")
    result["verdict"] = "TODO: real | duplicate | false_positive | not_a_bug | flaky"
    _write(out_dir, cand, result, stmts, culprit, check, shown, run)
    log(f"  reduced to {result['reduced']['statements']} statement(s), "
        f"{result['reduced']['culprit_tokens']} tokens in the culprit ({run.runs} runs, {result['seconds']} s)")
    return result


def _queries_to_show(cand: Candidate, stmts: list[str], culprit: int, check: dict[str, Any] | None) -> dict[str, str]:
    if check is not None:
        return {"lhs": check.get("lhs") or stmts[culprit], "rhs": str(check["rhs"])}
    if cand.outcome is Outcome.WRONG_RESULT:
        return {"query": stmts[culprit]}
    return {}


def reduced_sql(cand: Candidate, stmts: list[str], culprit: int, check: dict[str, Any] | None) -> str:
    lines = [f"-- pgfuzz triage of {cand.signature}: {cand.outcome.value} via {cand.oracle_name}"]
    lines += [s.rstrip(";") + ";" for s in stmts[:culprit]]
    v = cand.details.get("variant")
    if check is not None:
        lines.append("-- the two queries below must return the same rows (as a multiset):")
        lines.append((check.get("lhs") or stmts[culprit]).rstrip(";") + ";")
        lines.append(str(check["rhs"]).rstrip(";") + ";")
    elif cand.outcome is Outcome.WRONG_RESULT and v and v != "xversion":
        lines.append("-- default plan:")
        lines.append(stmts[culprit].rstrip(";") + ";")
        lines.append(f"-- plan variant {v} (must return the same rows):")
        lines += [f"SET {k} = '{val}';" for k, val in (cand.details.get("settings") or {}).items()]
        lines.append(stmts[culprit].rstrip(";") + ";")
        lines += [f"RESET {k};" for k in (cand.details.get("settings") or {})]
    else:
        lines.append(stmts[culprit].rstrip(";") + ";")
    return "\n".join(lines) + "\n"


def _table(obs: dict[str, Any]) -> str:
    if "error" in obs:
        return f"    ERROR: {obs['error']}"
    rows = obs.get("rows") or []
    body = "\n".join("    " + " | ".join("NULL" if v is None else str(v) for v in r) for r in rows)
    more = f"\n    ... ({obs.get('row_count')} rows)" if obs.get("row_count", 0) > len(rows) else ""
    return (body or "    (no rows)") + more


def _write(out_dir: Path, cand: Candidate, result: dict[str, Any], stmts: list[str], culprit: int,
           check: dict[str, Any] | None, shown: dict[str, str] | None, run: Runner | None) -> None:
    d = out_dir / cand.signature
    d.mkdir(parents=True, exist_ok=True)
    sql = reduced_sql(cand, stmts, culprit, check)
    (d / "reduced.sql").write_text(sql, encoding="utf-8")
    (d / "triage.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    det = cand.details
    lines = [f"# {cand.outcome.value}: {(cand.message or det.get('message') or '').strip()[:120]}", "",
             f"* Oracle: **{cand.oracle_name}**, signature `{cand.signature}`",
             f"* Reproduced: {result.get('reproduced')} on {result.get('test_server', '?')}",
             f"* Reduced: {result.get('original', {}).get('statements')} -> {result.get('reduced', {}).get('statements', '?')} "
             f"statements, {result.get('original', {}).get('culprit_tokens')} -> "
             f"{result.get('reduced', {}).get('culprit_tokens', '?')} tokens",
             f"* Verdict: {result.get('verdict')}", "", "## Reproducer", "", "```sql", sql.rstrip(), "```", ""]
    if "assertion" in det:
        a = det["assertion"]
        lines += ["## Assertion", "", f"`TRAP: failed Assert(\"{a.get('expr')}\"), File: \"{a.get('file')}\", Line: {a.get('line')}`", ""]
    if det.get("backtrace"):
        lines += ["## Backtrace (top frames)", "", "```", *det["backtrace"][:15], "```", ""]
    if result.get("observed"):
        lines += ["## Observed on the test server", ""]
        for name, obs in result["observed"].items():
            lines += [f"`{name}`:", "", "```", _table(obs), "```", ""]
    if result.get("observed_reference"):
        lines += [f"## Observed on the reference server ({result.get('reference_server')})", ""]
        for name, obs in result["observed_reference"].items():
            lines += [f"`{name}`:", "", "```", _table(obs), "```", ""]
    lines += ["## Before filing", "",
              "1. Decide which side is right (SQL standard / documentation) and say why.",
              "2. Search pgsql-bugs and pgsql-hackers for the message / function names.",
              "3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.",
              "4. Record the verdict in triage/verdicts.yaml (it feeds the precision table)."]
    (d / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verdict_template(results: list[dict[str, Any]]) -> str:
    """YAML entries for triage/verdicts.yaml (one per triaged candidate)."""
    out = []
    for r in results:
        out.append(f"- signature: {r['signature']}\n  oracle: {r['oracle']}\n  outcome: {r['outcome']}\n"
                   f"  reproduced: \"{r['reproduced']}\"\n  verdict: {'flaky' if r.get('verdict') == 'flaky' else 'TODO'}"
                   f"\n  note: \"\"\n  upstream: \"\"\n")
    return "".join(out)

