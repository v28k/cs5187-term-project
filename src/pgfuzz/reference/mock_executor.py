"""A simulated PostgreSQL for exercising the runner, oracle, logs and reports
without a server. Behaviour is deterministic and crude:

* parse errors: unbalanced parentheses/quotes, unknown leading verb, dangling
  operator or keyword at the end, two operators or two commas in a row;
* semantic errors: references to tables that are neither in ``tables`` nor
  created earlier in the same test case (state does not leak between test cases);
* runtime errors: division by literal zero; ``pg_sleep`` -> timeout;
  ``pg_terminate_backend(pg_backend_pid())`` -> orderly termination;
* planted "bugs" on specific feature combinations (crash, assertion, internal error);
* coverage = number of distinct (feature, outcome) and feature-pair "edges".

Its numbers are meaningless for the paper; it exists so that every part of the
evaluation pipeline has a test.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from pgfuzz.core.interfaces import Executor
from pgfuzz.core.types import CoverageSample, ExecResult, StatementResult, StatementStatus, TestCase
from pgfuzz.eval.features import StmtView, feature_pairs, features_of

_VERBS = {"SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "VALUES", "EXPLAIN",
          "TABLE", "MERGE", "TRUNCATE", "VACUUM", "ANALYZE", "SET", "RESET", "BEGIN", "COMMIT", "ROLLBACK",
          "PREPARE", "EXECUTE", "DO", "CALL", "COPY", "GRANT", "REVOKE", "LOCK", "COMMENT", "SAVEPOINT",
          "RELEASE", "REFRESH", "CLUSTER", "REINDEX", "DECLARE", "FETCH", "CLOSE", "SHOW"}
_DANGLING = {"AND", "OR", "NOT", "FROM", "WHERE", "SELECT", "BY", "ON", "JOIN", "AS", ",", "(", "=", "+", "-",
             "*", "/", "<", ">", "IN", "IS", "CASE", "WHEN", "THEN", "ELSE", "UNION", "SET", "INTO", "VALUES", "::"}
_BINOPS = {"=", "<>", "<", ">", "<=", ">=", "+", "/", "%", "||", "::", "AND", "OR"}
_TABLE_CTX = {"FROM", "JOIN", "INTO", "UPDATE", "TABLE"}

# Planted bugs: (required features, outcome, message)
_PLANTED = [
    (frozenset({"join:lateral", "window:over"}), "crash", None),
    (frozenset({"group_by:grouping_sets", "subquery:scalar"}), "internal", "unrecognized node type: 312"),
    (frozenset({"cte:recursive", "setop:except"}), "assert", 'TRAP: failed Assert("node->plan != NULL"), File: "nodeRecursiveunion.c", Line: 120, PID: 4242'),
    (frozenset({"distinct:on", "window:frame"}), "internal", "variable not found in subplan target list"),
]


class MockExecutor(Executor):
    name = "mock"

    def __init__(self, tables: list[str] | None = None, latency_ms: float = 0.0, plant_bugs: bool = True) -> None:
        self.base_tables = {t.lower() for t in (tables or ["t0", "t1"])}
        self.latency_ms = float(latency_ms)
        self.plant_bugs = bool(plant_bugs)
        self.edges: set[str] = set()
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "simulated": True, "plant_bugs": self.plant_bugs,
                "tables": sorted(self.base_tables), "server_version": "mock"}

    def sample_coverage(self) -> CoverageSample | None:
        return CoverageSample(edges=len(self.edges))

    def _parse_error(self, sql: str, view: StmtView) -> str | None:
        w = view.words
        if not w:
            return "syntax error at end of input"
        if sql.count("'") % 2 or sql.count('"') % 2:
            return "unterminated quoted string"
        if w[0] not in _VERBS and w[0] != "(":
            return f'syntax error at or near "{w[0]}"'
        depth = 0
        for i, x in enumerate(w):
            depth += (x == "(") - (x == ")")
            if depth < 0:
                return 'syntax error at or near ")"'
            if i and x in _BINOPS and w[i - 1] in _BINOPS:
                return f'syntax error at or near "{x}"'
            if i and x == "," and w[i - 1] in (",", "("):
                return 'syntax error at or near ","'
        if depth:
            return "syntax error at end of input"
        if w[-1] in _DANGLING:
            return "syntax error at end of input"
        return None

    def _run(self, sql: str, tables: set[str]) -> tuple[StatementResult, list[str], bool]:
        """Returns (result, server log lines, connection lost)."""
        view = StmtView.of(sql)
        err = self._parse_error(sql, view)
        if err:
            self.edges.add("parse_error")
            return StatementResult(StatementStatus.ERROR, "42601", err), [], False

        low = sql.lower()
        w = view.words
        if "pg_terminate_backend" in low and "pg_backend_pid" in low:
            return StatementResult(StatementStatus.CONNECTION_LOST, "57P01",
                                   "terminating connection due to administrator command"), [], True
        if view.kind == "CREATE" and view.create_target() == "TABLE":
            names = [x for x in w[2:6] if x not in ("TEMP", "TEMPORARY", "UNLOGGED", "IF", "NOT", "EXISTS", "TABLE")]
            if names:
                tables.add(names[0].lower())
        local = set(tables) | {w[i].lower() for i in range(len(w) - 2) if w[i + 1] == "AS" and w[i + 2] == "("}
        for i, x in enumerate(w[:-1]):
            is_call = i + 2 < len(w) and w[i + 2] == "("
            if x in _TABLE_CTX and not is_call and w[i + 1] not in ("<ID>", "SELECT", "LATERAL", "ONLY", "IF") and w[i + 1].isidentifier():
                name = w[i + 1].lower()
                if view.kind == "CREATE" and x == "TABLE":
                    continue
                if name not in local:
                    self.edges.add("undefined_table")
                    return StatementResult(StatementStatus.ERROR, "42P01", f'relation "{name}" does not exist'), [], False

        feats = features_of(sql)
        for f in feats:
            self.edges.add(f"f:{f}")
        for a, b in feature_pairs(feats):
            self.edges.add(f"p:{a}|{b}")

        if self.plant_bugs:
            for need, kind, msg in _PLANTED:
                if need <= feats:
                    self.edges.add(f"bug:{kind}")
                    if kind == "crash":
                        return (StatementResult(StatementStatus.CONNECTION_LOST, None, "server closed the connection unexpectedly"),
                                ["LOG:  server process (PID 4242) was terminated by signal 11: Segmentation fault"], True)
                    if kind == "assert":
                        return (StatementResult(StatementStatus.CONNECTION_LOST, None, "server closed the connection unexpectedly"),
                                [msg, "LOG:  server process (PID 4242) was terminated by signal 6: Aborted"], True)
                    return StatementResult(StatementStatus.ERROR, "XX000", msg), [], False

        if "pg_sleep" in low:
            return StatementResult(StatementStatus.ERROR, "57014", "canceling statement due to statement timeout"), [], False
        if any(w[i] == "/" and w[i + 1] == "<NUM>" and _zero_literal(sql) for i in range(len(w) - 1)):
            return StatementResult(StatementStatus.ERROR, "22012", "division by zero"), [], False
        digest = int(hashlib.md5(sql.encode()).hexdigest()[:4], 16)
        return StatementResult(StatementStatus.OK, rows=digest % 7), [], False

    def execute(self, testcase: TestCase) -> ExecResult:
        assert self.started, "executor not started"
        t0 = time.perf_counter()
        tables = set(self.base_tables)
        results: list[StatementResult] = []
        log: list[str] = []
        lost = False
        for sql in testcase.statements:
            if lost:
                results.append(StatementResult(StatementStatus.SKIPPED))
                continue
            s0 = time.perf_counter()
            r, lines, lost = self._run(sql, tables)
            if self.latency_ms:
                time.sleep(self.latency_ms / 1000)
            r.duration_ms = (time.perf_counter() - s0) * 1000
            results.append(r)
            log += lines
        restarted = lost and any("terminated by signal" in line for line in log)
        return ExecResult(results, wall_ms=(time.perf_counter() - t0) * 1000, server_log=log, server_restarted=restarted)


def _zero_literal(sql: str) -> bool:
    s = sql.replace(" ", "")
    return "/0)" in s or s.endswith("/0") or "/0," in s or "/0;" in s
