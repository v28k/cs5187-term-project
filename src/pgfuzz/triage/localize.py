"""Localize a reduced wrong result: which part of PostgreSQL is wrong?

The oracles that found a candidate already say a lot together (plan section 0.3):

* the result changes when one planner method is switched off -> a planner pass,
  named by that setting;
* the metamorphic mismatch (or the disagreement with the release) stays under
  every planner setting -> a rewrite, constant folding or expression evaluation
  that planner settings do not toggle;
* it disappears only under a few settings -> those code paths.

``localize`` re-runs the reduced queries under every plan variant (in rolled-back
transactions, after the setup statements) and reports, per variant, whether the
answer equals the default answer and, for paired queries, whether the two sides
agree. ``SUSPECTS`` maps each setting to the source files it switches, which goes
into the report so a developer knows where to start reading.
"""

from __future__ import annotations

from typing import Any

from pgfuzz.eval import differential as diff

SUSPECTS = {
    "enable_hashjoin": "executor/nodeHashjoin.c, optimizer/path/joinpath.c",
    "enable_mergejoin": "executor/nodeMergejoin.c, optimizer/path/joinpath.c",
    "enable_nestloop": "executor/nodeNestloop.c, optimizer/path/joinpath.c",
    "enable_hashagg": "executor/nodeAgg.c (hash), optimizer/plan/planner.c",
    "enable_incremental_sort": "executor/nodeIncrementalSort.c, optimizer/path/pathkeys.c",
    "enable_presorted_aggregate": "optimizer/plan/planner.c (presorted aggregates)",
    "enable_seqscan": "optimizer/path/indxpath.c, executor/nodeIndexscan.c",
    "enable_indexscan": "executor/nodeIndexscan.c, access/nbtree",
    "enable_indexonlyscan": "executor/nodeIndexonlyscan.c",
    "enable_bitmapscan": "executor/nodeBitmapHeapscan.c, optimizer/path/indxpath.c",
    "enable_memoize": "executor/nodeMemoize.c",
    "enable_material": "executor/nodeMaterial.c",
    "debug_parallel_query": "executor/execParallel.c, nodeGather.c",
    "enable_partitionwise_join": "optimizer/path/joinrels.c (partitionwise join)",
    "enable_partitionwise_aggregate": "optimizer/plan/planner.c (partitionwise aggregate)",
    "enable_partition_pruning": "partitioning/partprune.c, executor/execPartition.c",
    "geqo": "optimizer/geqo",
    "join_collapse_limit": "optimizer/plan/initsplan.c (join reordering)",
    "work_mem": "spilling paths: nodeHash.c batching, nodeAgg.c spill, tuplesort.c",
    "enable_group_by_reordering": "optimizer/path/pathkeys.c (GROUP BY reordering)",
    "enable_distinct_reordering": "optimizer/plan/planner.c (DISTINCT reordering)",
    "enable_self_join_elimination": "optimizer/plan/analyzejoins.c (self-join elimination)",
    "enable_eager_aggregate": "optimizer/path/allpaths.c, optimizer/util/relnode.c (eager aggregation)",
    "jit": "jit/llvm",
}


def _digest(ex: Any, setup: list[str], sql: str, settings: dict[str, str]) -> dict[str, Any]:
    import psycopg

    base = getattr(ex, "test", ex)
    if not base._alive():
        base._connect(wait=True)
    conn = base.conn
    out: dict[str, Any]
    try:
        conn.execute("BEGIN")
        for s in setup:
            conn.execute("SAVEPOINT l")
            try:
                conn.execute(s)
                conn.execute("RELEASE SAVEPOINT l")
            except psycopg.Error:
                conn.execute("ROLLBACK TO SAVEPOINT l")
        for k, v in settings.items():
            conn.execute("SELECT set_config(%s, %s, true)", (k, v))
        cur = conn.execute(sql)
        rows = cur.fetchall() if cur.description is not None else []
        h, n = diff.result_digest(rows, [c.type_code for c in cur.description or []], diff.masks_floats(sql))
        out = {"hash": h, "rows": n}
    except psycopg.Error as e:
        out = {"error": f"{getattr(e, 'sqlstate', '')} {str(e).splitlines()[0][:160]}"}
    finally:
        try:
            if base._alive():
                conn.execute("ROLLBACK")
        except psycopg.Error:
            pass
    return out


def localize(ex: Any, setup: list[str], queries: dict[str, str], reference: Any = None,
             variants: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    """``queries``: one query (plan-variant candidate) or two that must agree
    (metamorphic: ``lhs``/``rhs``; cross-version: the query on both servers)."""
    variants = variants if variants is not None else diff.DEFAULT_VARIANTS
    base = getattr(ex, "test", ex)
    if not base._alive():
        base._connect(wait=True)
    known = {r[0] for r in base.conn.execute("SELECT name FROM pg_settings").fetchall()}
    variants = {n: s for n, s in variants.items() if s and all(k in known for k in s)}   # this server's settings
    names = list(queries)
    default = {q: _digest(ex, setup, sql, {}) for q, sql in queries.items()}
    ref = _digest(reference, setup, queries[names[0]], {}) if reference is not None else None
    per: dict[str, Any] = {}
    for vname, settings in variants.items():
        got = {q: _digest(ex, setup, sql, settings) for q, sql in queries.items()}
        row: dict[str, Any] = {"changes_answer": any(got[q].get("hash") != default[q].get("hash") for q in names)}
        if len(names) == 2:
            row["sides_agree"] = got[names[0]].get("hash") == got[names[1]].get("hash")
        if ref is not None:
            row["agrees_with_release"] = got[names[0]].get("hash") == ref.get("hash")
        per[vname] = row
    return {"default": default, "reference": ref, "variants": per, "verdict": _verdict(names, default, ref, per, variants)}


def _verdict(names, default, ref, per, variants) -> dict[str, Any]:
    if len(names) == 2:
        default_agree = default[names[0]].get("hash") == default[names[1]].get("hash")
        fixed_by = [v for v, r in per.items() if r["sides_agree"]] if not default_agree else []
        kind = "sides_agree_by_default" if default_agree else (
            "planner" if fixed_by else "not_toggled_by_planner_settings")
    elif ref is not None:
        fixed_by = [v for v, r in per.items() if r.get("agrees_with_release")]
        kind = "planner" if fixed_by else "not_toggled_by_planner_settings"
    else:
        fixed_by = [v for v, r in per.items() if r["changes_answer"]]
        kind = "planner" if fixed_by else "no_variant_changes_the_answer"
    settings = sorted({k for v in fixed_by for k in variants.get(v, {})})
    return {"kind": kind, "variants": fixed_by, "settings": settings,
            "suspects": {k: SUSPECTS[k] for k in settings if k in SUSPECTS},
            "summary": _summary(kind, fixed_by)}


def _summary(kind: str, fixed_by: list[str]) -> str:
    if kind == "planner":
        return ("the answer depends on planner settings: " + ", ".join(fixed_by)
                + "; the code paths these switch are the first suspects")
    if kind == "not_toggled_by_planner_settings":
        return ("no planner setting removes the disagreement: suspect an always-applied rewrite, constant "
                "folding, a planner support function, or expression evaluation")
    if kind == "sides_agree_by_default":
        return "the two sides agree on the reduced case under default settings (check the reduction)"
    return "no plan variant changes the answer"
