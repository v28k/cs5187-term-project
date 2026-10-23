"""Executor for a real (ideally assert-enabled, coverage-instrumented) PostgreSQL.

Isolation modes (``isolation`` parameter):

``savepoint`` (default)
    Each test case runs inside ``BEGIN ... ROLLBACK``; each statement inside its
    own savepoint so an error does not abort later statements. No state leaks
    between test cases. Statements that cannot run in a transaction block
    (``VACUUM``, ``CREATE DATABASE``, ``... CONCURRENTLY``) fail with 25001, and
    transaction-control statements written by the generator (``COMMIT``,
    ``ROLLBACK``) end the outer transaction; the executor then reopens it, runs
    ``reset_sql`` after the test case and reports ``extra.state_leak``.
``autocommit``
    Statements run one by one in autocommit mode (reaches non-transactional
    code paths), and ``reset_sql`` runs after every test case to restore state.

Crash handling: when the connection drops, the statement is reported as
``CONNECTION_LOST`` (with the SQLSTATE if the server sent one), remaining
statements as ``SKIPPED``, and the executor waits for the postmaster to finish
crash recovery before returning. If ``server_log`` points at the server's log
file (mount it from the container), new lines are attached to every result so
the oracle can see ``TRAP:`` (assertion), ``PANIC:`` and ``terminated by signal``.

Coverage: if ``coverage_command`` is set, it is run (through the shell) every
``coverage_interval_s`` and must print JSON such as
``{"lines_covered": 123, "lines_total": 456, "branches_covered": 7, "branches_total": 9}``.
gcov writes ``.gcda`` files when a backend exits, so with ``coverage_reconnect``
(default on) the executor reconnects before running the command.
``coverage_reset_command`` runs once in ``start()``, before connecting, so every
trial starts from zero counters (otherwise trial k inherits trial k-1's coverage).

Differential oracle (``differential``): every successful statement that passes
``pgfuzz.eval.differential.eligible`` is re-run under ``per_query`` plan variants
(``SET LOCAL`` planner settings inside a savepoint that is rolled back), and the
result digests are recorded in ``StatementResult.result_hash`` / ``variants``.
The oracle reports a mismatch as ``wrong_result``, an internal error under a
variant as ``internal_error`` and a lost connection as a crash. Set it to
``true`` for the defaults or to ``{variants: [names...], per_query: 2, max_rows: 10000}``.

Metamorphic checks (``metamorphic``): when the generator attached follow-up
queries to a statement (``TestCase.meta["checks"]``, built on the derivation
tree by ``pgfuzz.grammar.rewrite``), both sides of every check run after the
statement succeeded, each in a savepoint that is rolled back, and their result
digests are recorded in ``StatementResult.checks``. A mismatch is re-run once
(``confirm``) and only counts if both sides return the same digests again, so
non-deterministic queries do not produce reports. ``true`` or
``{confirm: true, max_per_testcase: 6}``.

Plan shapes (``plan_shapes``): every ``every``-th successful read-only query is
also run under ``EXPLAIN (FORMAT JSON, COSTS OFF)`` and the tree of plan node
types is digested into ``StatementResult.plan_shape``; guided generators keep
test cases that reach a new plan shape (Query Plan Guidance, Ba and Rigger,
ICSE 2023). ``true`` or ``{every: 1}``.

Results are loaded as text (PostgreSQL's output format) so that values the
client cannot convert (``'infinity'::date``, years > 9999, ...) are not
misreported as errors, and result digests are exact.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from pgfuzz.core.interfaces import Executor
from pgfuzz.core.types import CoverageSample, ExecResult, StatementResult, StatementStatus, TestCase
from pgfuzz.eval import differential as diff

_COPY_STDIO = re.compile(r"^\s*(?:\\?copy)\b.*\b(?:stdin|stdout)\b", re.I | re.S)
_TXN_CONTROL = re.compile(r"^\s*(?:begin|start\s+transaction|commit|end|rollback|abort|prepare\s+transaction|commit\s+prepared|rollback\s+prepared)\b", re.I)


class PostgresExecutor(Executor):
    name = "postgres"

    def __init__(
        self,
        dsn: str = "host=localhost port=5432 dbname=postgres user=postgres",
        isolation: str = "savepoint",
        statement_timeout_ms: int = 5000,
        setup_sql: list[str] | str | None = None,
        reset_sql: list[str] | str | None = None,
        session_sql: list[str] | None = None,
        server_log: str | None = None,
        coverage_command: str | None = None,
        coverage_reset_command: str | None = None,
        coverage_reconnect: bool = True,
        coverage_timeout_s: float = 300,
        recovery_timeout_s: float = 120,
        crash_log_wait_s: float = 1.0,
        differential: bool | dict[str, Any] = False,
        metamorphic: bool | dict[str, Any] = False,
        plan_shapes: bool | dict[str, Any] = False,
        digests: bool = False,
        text_results: bool = True,
    ) -> None:
        if isolation not in ("savepoint", "autocommit"):
            raise ValueError("isolation must be 'savepoint' or 'autocommit'")
        self.dsn = dsn
        self.isolation = isolation
        self.statement_timeout_ms = int(statement_timeout_ms)
        self.setup_sql = _load_sql(setup_sql)
        self.reset_sql = _load_sql(reset_sql)
        self.session_sql = list(session_sql or [])
        self.server_log = Path(server_log) if server_log else None
        self.coverage_command = coverage_command
        self.coverage_reset_command = coverage_reset_command
        self.coverage_reconnect = bool(coverage_reconnect)
        self.coverage_timeout_s = float(coverage_timeout_s)
        self.recovery_timeout_s = float(recovery_timeout_s)
        self.crash_log_wait_s = float(crash_log_wait_s)
        self.text_results = bool(text_results)
        d = differential if isinstance(differential, dict) else ({} if differential else None)
        self.diff_enabled = d is not None
        self.digests = bool(digests)   # digest eligible results even without plan variants (cross-version)
        self.diff_per_query = int((d or {}).get("per_query", 2))
        self.diff_max_rows = int((d or {}).get("max_rows", 10000))
        wanted = (d or {}).get("variants")
        if isinstance(wanted, dict):
            self.variants = {str(k): {str(a): str(b) for a, b in v.items()} for k, v in wanted.items()}
        else:
            names = list(wanted) if wanted else list(diff.DEFAULT_VARIANTS)
            unknown = [n for n in names if n not in diff.DEFAULT_VARIANTS]
            if unknown:
                raise ValueError(f"unknown plan variants {unknown}; known: {sorted(diff.DEFAULT_VARIANTS)}")
            self.variants = {n: dict(diff.DEFAULT_VARIANTS[n]) for n in names}
        self.diff_stats: dict[str, Any] = {"checked": 0, "variant_runs": 0}
        m = metamorphic if isinstance(metamorphic, dict) else ({} if metamorphic else None)
        self.mm_enabled = m is not None
        self.mm_confirm = bool((m or {}).get("confirm", True))
        self.mm_max = int((m or {}).get("max_per_testcase", 6))
        ps = plan_shapes if isinstance(plan_shapes, dict) else ({} if plan_shapes else None)
        self.plan_every = int((ps or {}).get("every", 1)) if ps is not None else 0
        self._plan_n = 0
        self.conn: Any = None
        self._log_pos = 0
        self._info: dict[str, Any] = {}

    # ------------------------------------------------------------------ lifecycle

    def start(self) -> None:
        try:
            import psycopg  # noqa: F401
        except ImportError as e:
            raise RuntimeError("PostgresExecutor needs psycopg 3: pip install 'psycopg[binary]'") from e
        if self.coverage_reset_command:
            out = subprocess.run(self.coverage_reset_command, shell=True, capture_output=True, text=True,
                                 timeout=self.coverage_timeout_s)
            if out.returncode != 0:
                raise RuntimeError(f"coverage_reset_command failed ({out.returncode}): {out.stderr.strip()[:500]}")
        self._connect(wait=True)
        if self.setup_sql:
            for sql in self.setup_sql:
                self.conn.execute(sql)
        self._info = self._query_info()
        if self.diff_enabled:
            self._probe_variants()
        if self.server_log and self.server_log.exists():
            self._log_pos = self.server_log.stat().st_size

    def _probe_variants(self) -> None:
        """Drop settings the server does not know (older versions), and empty variants."""
        known = {r[0] for r in self.conn.execute("SELECT name FROM pg_settings").fetchall()}
        try:
            jit = self.conn.execute("SELECT pg_jit_available()").fetchone()[0] in (True, "t", "true")
        except Exception:
            jit = False
        kept = {}
        for name, settings in self.variants.items():
            s = {k: v for k, v in settings.items() if k in known}
            if s and not (name == "jit" and not jit):
                kept[name] = s
        self._info["plan_variants"] = sorted(kept)
        self._info["plan_variants_dropped"] = sorted(set(self.variants) - set(kept))
        self.variants = kept

    def stop(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def _connect(self, wait: bool) -> None:
        import psycopg

        deadline = time.monotonic() + (self.recovery_timeout_s if wait else 0)
        last: Exception | None = None
        while True:
            try:
                self.conn = psycopg.connect(self.dsn, autocommit=True, cursor_factory=psycopg.ClientCursor)
                if self.text_results:
                    _load_everything_as_text(self.conn)
                self.conn.execute(f"SET statement_timeout = {self.statement_timeout_ms}")
                for sql in self.session_sql:
                    self.conn.execute(sql)
                return
            except psycopg.OperationalError as e:  # server restarting / in recovery (57P03)
                last = e
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"cannot connect to PostgreSQL ({self.dsn}): {e}") from last
                time.sleep(0.5)

    def _query_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {}
        for key, sql in (
            ("server_version", "SHOW server_version"),
            ("version", "SELECT version()"),
            ("debug_assertions", "SHOW debug_assertions"),
            ("data_checksums", "SHOW data_checksums"),
        ):
            try:
                info[key] = self.conn.execute(sql).fetchone()[0]
            except Exception:
                info[key] = None
        return info

    def describe(self) -> dict[str, Any]:
        d = {"name": self.name, "isolation": self.isolation, "statement_timeout_ms": self.statement_timeout_ms,
             "server_log": str(self.server_log) if self.server_log else None,
             "coverage": bool(self.coverage_command), "differential": self.diff_enabled,
             "metamorphic": self.mm_enabled, "plan_shapes_every": self.plan_every,
             "diff_per_query": self.diff_per_query if self.diff_enabled else None, **self._info}
        if self._info.get("debug_assertions") == "off":
            d["warning"] = "server built without --enable-cassert: assertion failures cannot be observed"
        return d

    # ------------------------------------------------------------------ execution

    def _new_log_lines(self) -> list[str]:
        if not self.server_log or not self.server_log.exists():
            return []
        size = self.server_log.stat().st_size
        if size < self._log_pos:  # rotated or truncated
            self._log_pos = 0
        if size == self._log_pos:
            return []
        with self.server_log.open("rb") as f:
            f.seek(self._log_pos)
            data = f.read(size - self._log_pos)
        self._log_pos = size
        return data.decode("utf-8", errors="replace").splitlines()

    def _alive(self) -> bool:
        return self.conn is not None and not self.conn.closed and not getattr(self.conn, "broken", False)

    def execute(self, testcase: TestCase) -> ExecResult:
        import psycopg

        if not self._alive():
            self._connect(wait=True)

        t0 = time.perf_counter()
        results: list[StatementResult] = []
        lost = False
        leak = False
        in_txn = self.isolation == "savepoint"
        if in_txn:
            self.conn.execute("BEGIN")
        checks_by_stmt: dict[int, list[dict[str, Any]]] = {}
        if self.mm_enabled:
            for c in (testcase.meta.get("checks") or [])[: self.mm_max]:
                checks_by_stmt.setdefault(int(c.get("stmt", -1)), []).append(c)

        for idx, sql in enumerate(testcase.statements):
            if lost:
                results.append(StatementResult(StatementStatus.SKIPPED))
                continue
            if _COPY_STDIO.match(sql):
                results.append(StatementResult(StatementStatus.ERROR, "0A000", "pgfuzz: COPY FROM STDIN / TO STDOUT is not supported by the executor"))
                continue
            s0 = time.perf_counter()
            run_variants = self.diff_enabled and bool(self.variants)
            check = (run_variants or self.digests) and diff.eligible(sql)
            my_checks = checks_by_stmt.get(idx, [])
            n_before = len(results)
            try:
                if in_txn:
                    self.conn.execute("SAVEPOINT pgfuzz_sp")
                cur = self.conn.execute(sql)
                rows = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else None
                digest = None
                data: list[Any] = []
                types: list[int] = []
                if cur.description is not None:
                    data = cur.fetchall()
                    types = [c.type_code for c in cur.description]
                    rows = len(data)
                    if check:
                        digest, _ = diff.result_digest(data, types, diff.masks_floats(sql), self.diff_max_rows)
                st = StatementResult(StatementStatus.OK, duration_ms=_ms(s0), rows=rows, result_hash=digest)
                results.append(st)
                idle = False
                if in_txn:
                    if self._txn_status() == "idle":
                        leak = idle = True
                        self.conn.execute("BEGIN")
                    else:
                        self.conn.execute("RELEASE SAVEPOINT pgfuzz_sp")
                if digest is not None and not idle and run_variants:
                    st.variants = self._run_variants(sql)
                    lost_v = next((n for n, v in st.variants.items() if v["status"] == "connection_lost"), None)
                    if lost_v is not None:
                        st.status = StatementStatus.CONNECTION_LOST
                        st.sqlstate = st.variants[lost_v].get("sqlstate")
                        st.message = f"server connection lost while running plan variant {lost_v}"
                        lost = True
                if my_checks and not idle and not lost and cur.description is not None:
                    st.checks = self._run_checks(sql, data, types, my_checks)
                    lost_c = next((c for c in st.checks if c["status"] == "connection_lost"), None)
                    if lost_c is not None:
                        st.status = StatementStatus.CONNECTION_LOST
                        st.sqlstate = lost_c.get("sqlstate")
                        st.message = f"server connection lost while running metamorphic check {lost_c['kind']}"
                        lost = True
                if self.plan_every and not idle and not lost and cur.description is not None and in_txn \
                        and diff.eligible(sql):
                    self._plan_n += 1
                    if self._plan_n % self.plan_every == 0:
                        st.plan_shape = self._plan_shape(sql)
            except psycopg.Error as e:
                del results[n_before:]  # the statement may have succeeded before RELEASE failed
                sqlstate = getattr(e, "sqlstate", None)
                msg = _message(e)
                if not self._alive():
                    lost = True
                    results.append(StatementResult(StatementStatus.CONNECTION_LOST, sqlstate, msg, _ms(s0)))
                    continue
                results.append(StatementResult(StatementStatus.ERROR, sqlstate, msg, _ms(s0)))
                if in_txn:
                    try:
                        status = self._txn_status()
                        if status == "inerror":
                            self.conn.execute("ROLLBACK TO SAVEPOINT pgfuzz_sp")
                        elif status == "idle":
                            leak = leak or bool(_TXN_CONTROL.match(sql))
                            self.conn.execute("BEGIN")
                    except psycopg.Error:
                        self._reopen_txn()
            except Exception as e:  # client-side problems (e.g. undecodable result)
                del results[n_before:]
                results.append(StatementResult(StatementStatus.ERROR, None, f"pgfuzz client error: {type(e).__name__}: {e}", _ms(s0)))
                if in_txn and self._alive():
                    self._reopen_txn()

        restarted = False
        if lost:
            time.sleep(self.crash_log_wait_s)
            self.conn = None
            self._connect(wait=True)
            restarted = True
        elif in_txn and self._alive():
            try:
                self.conn.execute("ROLLBACK")
            except psycopg.Error:
                pass
        if self.reset_sql and (self.isolation == "autocommit" or leak or lost):
            self._reset()
        # Crash, assertion, PANIC and sanitizer evidence only ever accompanies a failing
        # statement, so the log (slow on network/WSL mounts) is read only then. Lines
        # left over from earlier, successful test cases carry no such evidence.
        failed = lost or any(st.status is not StatementStatus.OK
                             or any(v.get("status") != "ok" for v in (st.variants or {}).values())
                             for st in results)
        log = self._new_log_lines() if failed else []
        return ExecResult(results, wall_ms=_ms(t0), server_log=log, server_restarted=restarted,
                          extra={"state_leak": True} if leak else {})

    def _run_variants(self, sql: str) -> dict[str, dict[str, Any]]:
        """Re-run ``sql`` under plan variants; every run is rolled back. Stops at a lost connection."""
        import psycopg

        self.diff_stats["checked"] += 1
        out: dict[str, dict[str, Any]] = {}
        sp = self.isolation == "savepoint"
        for name in diff.pick_variants(sql, sorted(self.variants), self.diff_per_query):
            settings = self.variants[name]
            rec: dict[str, Any] = {"settings": settings}
            s0 = time.perf_counter()
            self.diff_stats["variant_runs"] += 1
            try:
                self.conn.execute("SAVEPOINT pgfuzz_v" if sp else "BEGIN")
                for k, v in settings.items():
                    self.conn.execute("SELECT set_config(%s, %s, true)", (k, v))
                cur = self.conn.execute(sql)
                data = cur.fetchall() if cur.description is not None else []
                h, n = diff.result_digest(data, [c.type_code for c in cur.description or []],
                                          diff.masks_floats(sql), self.diff_max_rows)
                rec.update(status="ok", hash=h, rows=n)
            except psycopg.Error as e:
                if not self._alive():
                    rec.update(status="connection_lost", sqlstate=getattr(e, "sqlstate", None), message=_message(e))
                    out[name] = rec
                    return out
                rec.update(status="error", sqlstate=getattr(e, "sqlstate", None), message=_message(e))
            except Exception as e:  # client-side decoding problems
                rec.update(status="client_error", message=f"{type(e).__name__}: {e}")
            rec["ms"] = round(_ms(s0), 3)
            out[name] = rec
            try:
                if sp:
                    self.conn.execute("ROLLBACK TO SAVEPOINT pgfuzz_v")
                    self.conn.execute("RELEASE SAVEPOINT pgfuzz_v")
                else:
                    self.conn.execute("ROLLBACK")
            except psycopg.Error:
                if not self._alive():
                    rec.update(status="connection_lost")
                    return out
                if sp:
                    self._reopen_txn()
        return out

    def run_outside(self, statements: list[str]) -> None:
        """Run statements in autocommit, outside any test case (best effort)."""
        import psycopg

        if not self._alive():
            self._connect(wait=True)
        for sql in statements:
            try:
                self.conn.execute(sql)
            except psycopg.Error:
                if not self._alive():
                    self._connect(wait=True)

    def _run_side(self, sql: str, mask: bool) -> dict[str, Any]:
        """Run one read-only query in a savepoint that is rolled back; digest the result."""
        import psycopg

        sp = self.isolation == "savepoint"
        rec: dict[str, Any] = {}
        try:
            self.conn.execute("SAVEPOINT pgfuzz_m" if sp else "BEGIN")
            cur = self.conn.execute(sql)
            data = cur.fetchall() if cur.description is not None else []
            h, n = diff.result_digest(data, [c.type_code for c in cur.description or []], mask, self.diff_max_rows)
            rec.update(status="ok", hash=h, rows=n)
        except psycopg.Error as e:
            if not self._alive():
                return {"status": "connection_lost", "sqlstate": getattr(e, "sqlstate", None), "message": _message(e)}
            rec.update(status="error", sqlstate=getattr(e, "sqlstate", None), message=_message(e))
        except Exception as e:  # client-side decoding problems
            rec.update(status="client_error", message=f"{type(e).__name__}: {e}")
        try:
            if sp:
                self.conn.execute("ROLLBACK TO SAVEPOINT pgfuzz_m")
                self.conn.execute("RELEASE SAVEPOINT pgfuzz_m")
            else:
                self.conn.execute("ROLLBACK")
        except psycopg.Error:
            if not self._alive():
                return {"status": "connection_lost", "sqlstate": None, "message": "lost while rolling back a check"}
            if sp:
                self._reopen_txn()
        return rec

    def _run_checks(self, sql: str, data: list[Any], types: list[int], checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Run the metamorphic checks of one successful statement (see ``pgfuzz.grammar.rewrite``)."""
        out: list[dict[str, Any]] = []
        st = self.diff_stats
        for c in checks:
            kind, lhs, rhs, mask = str(c.get("kind")), c.get("lhs"), str(c.get("rhs")), bool(c.get("mask"))
            st["mm_checks"] = st.get("mm_checks", 0) + 1
            st[f"mm_run:{kind.split(':')[0]}"] = st.get(f"mm_run:{kind.split(':')[0]}", 0) + 1
            rec: dict[str, Any] = {"kind": kind}
            if lhs is None:
                h, n = diff.result_digest(data, types, mask, self.diff_max_rows)
                left: dict[str, Any] = {"status": "ok", "hash": h, "rows": n}
            else:
                left = self._run_side(lhs, mask)
            right = self._run_side(rhs, mask) if left["status"] == "ok" else {"status": "skipped"}
            failed = left if left["status"] != "ok" else right if right["status"] not in ("ok", "skipped") else None
            if failed is not None:
                side = "lhs" if failed is left else "rhs"
                rec.update(status=failed["status"], side=side, sqlstate=failed.get("sqlstate"),
                           message=failed.get("message"), sql=lhs if side == "lhs" else rhs)
                st["mm_side_errors"] = st.get("mm_side_errors", 0) + 1
                out.append(rec)
                if failed["status"] == "connection_lost":
                    return out
                continue
            rec.update(status="ok", lhs_hash=left["hash"], rhs_hash=right["hash"],
                       lhs_rows=left["rows"], rhs_rows=right["rows"])
            if left["hash"] is not None and right["hash"] is not None and left["hash"] != right["hash"]:
                rec.update(lhs_sql=lhs, rhs_sql=rhs)
                if self.mm_confirm:
                    left2 = self._run_side(lhs if lhs is not None else sql, mask)
                    right2 = self._run_side(rhs, mask)
                    if "connection_lost" in (left2["status"], right2["status"]):
                        rec.update(status="connection_lost", message="lost while confirming a check")
                        out.append(rec)
                        return out
                    rec["confirmed"] = (left2.get("hash") == left["hash"] and right2.get("hash") == right["hash"])
                else:
                    rec["confirmed"] = True
                key = "mm_mismatch" if rec["confirmed"] else "mm_unconfirmed"
                st[key] = st.get(key, 0) + 1
            out.append(rec)
        return out

    def _plan_shape(self, sql: str) -> str | None:
        """Digest of the plan's node structure for ``sql`` (costs and row counts ignored)."""
        import hashlib

        import psycopg

        try:
            self.conn.execute("SAVEPOINT pgfuzz_p")
            row = self.conn.execute(f"EXPLAIN (FORMAT JSON, COSTS OFF) {sql}").fetchone()
            self.conn.execute("ROLLBACK TO SAVEPOINT pgfuzz_p")
            self.conn.execute("RELEASE SAVEPOINT pgfuzz_p")
        except psycopg.Error:
            if self._alive():
                try:
                    self.conn.execute("ROLLBACK TO SAVEPOINT pgfuzz_p")
                    self.conn.execute("RELEASE SAVEPOINT pgfuzz_p")
                except psycopg.Error:
                    self._reopen_txn()
            return None
        try:
            plan = json.loads(row[0])[0]["Plan"] if isinstance(row[0], str) else row[0][0]["Plan"]
        except (ValueError, KeyError, IndexError, TypeError):
            return None
        shape = plan_shape_string(plan)
        self.diff_stats["plan_shapes_sampled"] = self.diff_stats.get("plan_shapes_sampled", 0) + 1
        return hashlib.blake2b(shape.encode(), digest_size=8).hexdigest()

    def _txn_status(self) -> str:
        from psycopg.pq import TransactionStatus

        st = self.conn.info.transaction_status
        return {TransactionStatus.IDLE: "idle", TransactionStatus.INTRANS: "intrans",
                TransactionStatus.INERROR: "inerror"}.get(st, "unknown")

    def _reopen_txn(self) -> None:
        import psycopg

        try:
            self.conn.execute("ROLLBACK")
            self.conn.execute("BEGIN")
        except psycopg.Error:
            self.conn = None
            self._connect(wait=True)
            self.conn.execute("BEGIN")

    def _reset(self) -> None:
        import psycopg

        for sql in self.reset_sql:
            try:
                self.conn.execute(sql)
            except psycopg.Error:
                if not self._alive():
                    self._connect(wait=True)

    # ------------------------------------------------------------------ coverage

    def sample_coverage(self) -> CoverageSample | None:
        if not self.coverage_command:
            return None
        if self.coverage_reconnect:
            self.stop()
            time.sleep(0.2)
        try:
            out = subprocess.run(self.coverage_command, shell=True, capture_output=True, text=True,
                                 timeout=self.coverage_timeout_s)
        finally:
            if self.coverage_reconnect:
                self._connect(wait=True)
        if out.returncode != 0:
            raise RuntimeError(f"coverage_command failed ({out.returncode}): {out.stderr.strip()[:500]}")
        data = json.loads(out.stdout.strip().splitlines()[-1])
        fields = CoverageSample.__dataclass_fields__
        return CoverageSample(**{k: int(v) for k, v in data.items() if k in fields and v is not None})


# Plan properties that distinguish algorithms; relation names, costs and row
# estimates do not count, so the shape is stable across data and literals.
_PLAN_KEYS = ("Node Type", "Join Type", "Strategy", "Partial Mode", "Parallel Aware", "Command",
              "Scan Direction", "Subplan Name", "Parent Relationship")


def plan_shape_string(plan: dict[str, Any]) -> str:
    """Canonical text of a plan tree's shape, e.g. ``Hash Join[Inner](Seq Scan,Hash(Seq Scan))``."""
    label = "|".join(str(plan[k]) for k in _PLAN_KEYS if k in plan and plan[k] not in (False, None))
    kids = plan.get("Plans") or []
    if not kids:
        return label
    return f"{label}(" + ",".join(plan_shape_string(k) for k in kids) + ")"


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def _load_everything_as_text(conn: Any) -> None:
    """Return every column as PostgreSQL's text output instead of Python objects."""
    import psycopg
    from psycopg.types.string import TextLoader

    for t in psycopg.postgres.types:
        for oid in (t.oid, getattr(t, "array_oid", 0)):
            if oid:
                conn.adapters.register_loader(oid, TextLoader)


def _message(e: Exception) -> str:
    diag = getattr(e, "diag", None)
    primary = getattr(diag, "message_primary", None) if diag is not None else None
    if primary:
        return primary
    text = str(e).strip()
    return text.splitlines()[0] if text else type(e).__name__


def _load_sql(v: list[str] | str | None) -> list[str]:
    """Inline statements, or a path to a .sql file."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    p = Path(v)
    if p.suffix == ".sql" and p.exists():
        from pgfuzz.core.sqlsplit import split_statements

        return split_statements(p.read_text(encoding="utf-8"))
    return [v]
