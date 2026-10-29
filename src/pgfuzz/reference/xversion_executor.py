"""Cross-version differential executor: the same test case on two PostgreSQL versions.

Every test case runs on the server under test (usually ``master``, assertions
on) and on a reference server (usually the latest release branch). For each
statement that succeeded on both and is deterministic
(:func:`pgfuzz.eval.differential.eligible`), the result digests are compared.
A difference is recorded as a pseudo plan variant named ``xversion`` on the
test side, so the oracle reports it as ``wrong_result`` (variant ``xversion``)
through the same path as the plan-variant oracle, and it is deduplicated and
reported the same way.

Why this finds bugs the other oracles miss: a new optimisation in ``master``
that is wrong under *every* planner setting (no plan variant turns it off) still
disagrees with a release that does not have the optimisation. Regressions in
unreleased code are also what upstream fixes fastest (open items).

Not every difference is a bug: behaviour changes between versions are sometimes
intentional (release notes); triage checks those. Statements that fail on only
one side are counted but not reported (new features, new errors).

Config::

    executor:
      plugin: pgfuzz.reference.xversion_executor:CrossVersionExecutor
      params:
        test:      {dsn: "host=127.0.0.1 port={port} ...", server_log: ..., differential: {per_query: 2}}
        reference: {dsn: "host=127.0.0.1 port=5435 ...", statement_timeout_ms: 3000}
        prelude_sql: ["ALTER TABLE t2 ALTER COLUMN c0 RESTART WITH 31"]

``prelude_sql`` runs on both servers before every test case, outside its
transaction. Sequences are not transactional, so a test case that inserts on
only one server would otherwise shift identity values apart for the rest of
the run. Statements that read the clock or the server instance are never
compared (:func:`pgfuzz.eval.differential.xversion_eligible`).
"""

from __future__ import annotations

from typing import Any

from pgfuzz.core.interfaces import Executor
from pgfuzz.core.types import CoverageSample, ExecResult, StatementStatus, TestCase
from pgfuzz.eval.differential import xversion_eligible
from pgfuzz.reference.pg_executor import PostgresExecutor


_STATE_VERBS = frozenset({"INSERT", "UPDATE", "DELETE", "MERGE", "CREATE", "ALTER", "DROP", "TRUNCATE", "COPY",
                          "REFRESH", "ANALYZE", "VACUUM", "CLUSTER", "REINDEX", "WITH"})


def _changes_state(sql: str) -> bool:
    """Could this statement change table contents or the schema? (WITH may hide a DML.)"""
    words = sql.lstrip().split(None, 1)
    return bool(words) and words[0].upper().strip("(") in _STATE_VERBS


class CrossVersionExecutor(Executor):
    name = "xversion"

    def __init__(self, test: dict[str, Any], reference: dict[str, Any], prelude_sql: list[str] | None = None) -> None:
        self.prelude = list(prelude_sql or [])
        test = dict(test)
        reference = dict(reference)
        test["digests"] = True
        reference["digests"] = True
        # The reference only has to return digests; it runs no oracles of its own.
        for k in ("differential", "metamorphic", "plan_shapes", "coverage_command", "coverage_reset_command"):
            reference.pop(k, None)
        for k in ("setup_sql", "reset_sql", "session_sql", "statement_timeout_ms"):
            if k in test and k not in reference:
                reference[k] = test[k]
        self.test = PostgresExecutor(**test)
        self.ref = PostgresExecutor(**reference)
        self.xstats = {"diverged": 0, "compared": 0, "mismatch": 0, "test_only_ok": 0, "ref_only_ok": 0, "ref_failures": 0}

    @property
    def diff_stats(self) -> dict[str, Any]:
        return {**self.test.diff_stats, **{f"xversion_{k}": v for k, v in self.xstats.items()}}

    def start(self) -> None:
        self.test.start()
        self.ref.start()
        self._ref_version = self.ref.describe().get("server_version")

    def stop(self) -> None:
        self.test.stop()
        self.ref.stop()

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "test": self.test.describe(), "reference": self.ref.describe()}

    def sample_coverage(self) -> CoverageSample | None:
        return self.test.sample_coverage()

    def execute(self, testcase: TestCase) -> ExecResult:
        if self.prelude:
            self.test.run_outside(self.prelude)
            self.ref.run_outside(self.prelude)
        res = self.test.execute(testcase)
        ref_tc = TestCase(list(testcase.statements), origin=testcase.origin,
                          meta={k: v for k, v in testcase.meta.items() if k != "checks"}, id=testcase.id)
        try:
            ref = self.ref.execute(ref_tc)
        except Exception as e:  # the reference must never stop the campaign
            self.xstats["ref_failures"] += 1
            res.extra["xversion_error"] = f"{type(e).__name__}: {e}"
            return res
        diverged = False       # a state-changing statement ran on one server only: the tables now differ
        for sql, st, rt in zip(testcase.statements, res.statements, ref.statements):
            t_ok, r_ok = st.status is StatementStatus.OK, rt.status is StatementStatus.OK
            if t_ok and not r_ok:
                self.xstats["test_only_ok"] += 1
            elif r_ok and not t_ok:
                self.xstats["ref_only_ok"] += 1
            if t_ok != r_ok and _changes_state(sql):
                diverged = True        # e.g. a PG19-only construct inside an INSERT ... SELECT
                self.xstats["diverged"] = self.xstats.get("diverged", 0) + 1
            if diverged or not (t_ok and r_ok) or st.result_hash is None or rt.result_hash is None \
                    or not xversion_eligible(sql):
                continue
            self.xstats["compared"] += 1
            if st.result_hash != rt.result_hash:
                self.xstats["mismatch"] += 1
                st.variants = dict(st.variants or {})
                st.variants["xversion"] = {"status": "ok", "hash": rt.result_hash, "rows": rt.rows,
                                           "settings": {"reference_server": str(self._ref_version)}}
        return res
