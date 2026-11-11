"""Target abstraction for in-process SQL engines (DuckDB, SQLite, Turso, DataFusion, ...).

An engine is described by a :class:`Driver`, a small class that runs *inside* a worker
process and knows how to connect, run one statement, name its errors, list and toggle
its optimizer rules and print a plan. Everything else is shared by
:class:`WorkerExecutor`:

* crash isolation: the driver lives in a spawned worker; a worker that dies is a crash
  (exit code / signal recorded), one that does not answer within the statement timeout
  is killed and the statement counted as a timeout;
* per-test-case isolation: the driver opens a transaction (or a fresh database) per test
  case; after an error in an engine whose transactions abort, the executor rolls back
  and replays the statements that succeeded;
* oracles: plan variants (one optimizer rule off, the whole optimizer off, ...) and the
  metamorphic checks attached by the grammar generator, compared by result digest;
* errors map to pseudo SQLSTATEs so :mod:`pgfuzz.eval.oracle` classifies them the same
  way for every engine (internal errors → ``XX000``).

Adding an engine = a Driver subclass + a dialect overlay + a schema.
"""

from __future__ import annotations

import importlib
import multiprocessing as mp
import random
import time
from pathlib import Path
from typing import Any

from pgfuzz.core.interfaces import Executor
from pgfuzz.core.types import ExecResult, StatementResult, StatementStatus, TestCase
from pgfuzz.eval import differential as diff


class Driver:
    """Engine adapter. Runs in the worker process; must be importable by path."""

    name = "engine"
    #: engine error class name -> pseudo SQLSTATE (see pgfuzz.eval.oracle)
    sqlstate: dict[str, str] = {}
    default_sqlstate = "22000"
    #: does an error abort the open transaction (so the executor must replay)?
    error_aborts_transaction = True
    #: type name prefix -> PostgreSQL type OID, for float/numeric masking in digests
    type_oids: dict[str, int] = {"DECIMAL": diff.NUMERIC_OID, "NUMERIC": diff.NUMERIC_OID, "DOUBLE": 701,
                                 "FLOAT": 700, "REAL": 700, "INTERVAL": diff.INTERVAL_OID}

    def __init__(self, **params: Any) -> None:
        self.params = params

    # -- lifecycle ---------------------------------------------------------------
    def connect(self, setup: list[str]) -> str:
        """Open the database, run ``setup`` and return the engine version."""
        raise NotImplementedError

    def close(self) -> None:
        pass

    def begin(self) -> None:
        """Start isolating one test case (default: a transaction)."""
        self.execute("BEGIN TRANSACTION", False, 0)

    def end(self) -> None:
        """Undo everything the test case did."""
        self.execute("ROLLBACK", False, 0)

    # -- statements --------------------------------------------------------------
    def execute(self, sql: str, fetch: bool, max_rows: int) -> tuple[list[tuple] | None, list[str] | None]:
        """Run one statement. Returns (rows, type names) or (None, None) for no result set.
        Raises the engine's own exception on error."""
        raise NotImplementedError

    def error_name(self, exc: BaseException) -> str | None:
        """Engine error class name, or None if ``exc`` is not an engine error."""
        return type(exc).__name__

    # -- optimizer rules / plans -------------------------------------------------
    def rules(self) -> list[str]:
        """Names of optimizer rules that can be switched off one at a time."""
        return []

    def variants(self) -> dict[str, Any]:
        """Plan variants: name -> opaque spec understood by :meth:`apply_variant`.
        Default: one variant per rule (``no_<rule>``)."""
        return {f"no_{r}": {"rules_off": [r]} for r in self.rules()}

    def apply_variant(self, spec: Any) -> None:
        raise NotImplementedError

    def variant_sql(self, spec: Any) -> list[str]:
        """SQL a human runs to reproduce the variant (for reports); empty if none."""
        return list(spec.get("sql", [])) if isinstance(spec, dict) else []

    def reset_variant(self) -> None:
        pass

    def explain(self, sql: str) -> str:
        """Normalised plan text (no costs, no row estimates)."""
        raise NotImplementedError

    #: query listing the user tables (one name per row); None switches the state-restoration oracle off
    state_tables_sql: str | None = None

    def state_fingerprint(self) -> str | None:
        """Cheap summary of the database contents (tables and their row counts), taken between
        test cases. After a test case is rolled back it must equal the value before it (the
        state-restoration oracle); an engine that keeps a change breaks every later comparison."""
        if not self.state_tables_sql:
            return None
        names = sorted(str(r[0]) for r in (self.execute(self.state_tables_sql, True, 100000)[0] or []))
        parts = []
        for n in names:
            try:
                rows = self.execute(f'SELECT count(*) FROM "{n}"', True, 10)[0]
                parts.append(f"{n}={rows[0][0] if rows else '?'}")
            except Exception as e:      # an unreadable table is a state change too
                parts.append(f"{n}=error:{type(e).__name__}")
        return " ".join(parts)

    def rules_off_spec(self, rules: list[str]) -> Any:
        """Variant spec that switches off all ``rules`` at once (group testing)."""
        return {"rules_off": list(rules)}

    def fired(self, sql: str, rules: list[str] | None = None) -> tuple[str, list[str]]:
        """Rule-firing probe: (base plan, rules whose removal changes the plan).

        A rule *fires* for a query when switching that rule off (and nothing else) changes
        the plan. This needs no instrumented build: only per-rule switches and EXPLAIN.
        Rules are tested one at a time: switching rules off is not monotone (on SQLite,
        MinMaxOpt off changes a plan that MinMaxOpt+QueryFlattener off leaves unchanged), so
        group testing would miss rules. The executor bounds the cost (sampling, plan cache,
        overhead budget, and it stops probing rules that fire for every query).
        """
        base = self.explain(sql)
        self._probe_explains = 1
        out = []
        for r in rules if rules is not None else self.rules():
            try:
                self.apply_variant(self.rules_off_spec([r]))
                other = self.explain(sql)
            except Exception:
                other = None
            finally:
                self.reset_variant()
            self._probe_explains += 1
            if other is not None and other != base:
                out.append(r)
        return base, out


def _render(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, (bytes, bytearray, memoryview)):
        return "\\x" + bytes(v).hex()
    return str(v)


def load_driver(path: str, params: dict[str, Any]) -> Driver:
    mod, _, cls = path.partition(":")
    return getattr(importlib.import_module(mod), cls)(**params)


def _worker(conn: Any, driver_path: str, driver_params: dict[str, Any], setup: list[str],
            stderr_path: str | None = None) -> None:
    """Worker process main loop (spawned)."""
    from pgfuzz.core.procs import die_with_parent

    die_with_parent()
    if stderr_path:   # panics / assertion messages of the engine end up here (read after a crash)
        import os

        fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        os.dup2(fd, 2)
        os.close(fd)
    drv = load_driver(driver_path, driver_params)
    try:
        version = drv.connect(setup)
    except Exception as e:  # setup failed: report and exit
        conn.send(("setup_error", f"{type(e).__name__}: {e}"))
        return
    conn.send(("ready", version))
    while True:
        try:
            msg = conn.recv()
        except EOFError:
            return
        op = msg[0]
        if op == "quit":
            drv.close()
            return
        try:
            if op == "exec":
                _, sql, fetch, max_rows = msg
                rows, types = drv.execute(sql, fetch, max_rows)
                if rows is not None:
                    rows = [tuple(_render(v) for v in r) for r in rows]
                conn.send(("ok", rows, types))
            elif op == "begin":
                drv.begin()
                conn.send(("ok", None, None))
            elif op == "end":
                drv.end()
                conn.send(("ok", None, None))
            elif op == "meta":
                vs = drv.variants()
                conn.send(("ok", {"rules": drv.rules(), "variants": sorted(vs),
                                  "variant_sql": {k: drv.variant_sql(v) for k, v in vs.items()},
                                  "aborts": drv.error_aborts_transaction}, None))
            elif op == "variant":
                spec = drv.variants().get(msg[1])
                if spec is None:
                    raise KeyError(f"unknown variant {msg[1]}")
                drv.apply_variant(spec)
                conn.send(("ok", None, None))
            elif op == "reset_variant":
                drv.reset_variant()
                conn.send(("ok", None, None))
            elif op == "state":
                conn.send(("ok", drv.state_fingerprint(), None))
            elif op == "explain":
                conn.send(("ok", drv.explain(msg[1]), None))
            elif op == "fired":
                base, rules = drv.fired(msg[1], msg[2] if len(msg) > 2 else None)
                conn.send(("ok", {"plan": base, "rules": rules, "explains": getattr(drv, "_probe_explains", 0)}, None))
            else:
                conn.send(("error", "ClientError", f"unknown op {op}"))
        except Exception as e:
            name = drv.error_name(e)
            if name is None:
                name = "ClientError"
            conn.send(("error", name, str(e)))


class WorkerExecutor(Executor):
    """Executor for an engine described by a :class:`Driver` (see module docstring)."""

    name = "engine"

    def __init__(self, driver: str, driver_params: dict[str, Any] | None = None,
                 setup_sql: list[str] | str | None = None, statement_timeout_ms: int = 5000,
                 differential: bool | dict[str, Any] = False, metamorphic: bool | dict[str, Any] = False,
                 max_rows: int = 10000, seed: int = 0, start_timeout_s: float = 120,
                 rule_feedback: bool | dict[str, Any] = False, normalize: list[str] | None = None,
                 state_check: bool = True) -> None:
        self.driver_path = driver
        self.driver_params = dict(driver_params or {})
        self.setup_sql = _load_sql(setup_sql)
        self.timeout_s = statement_timeout_ms / 1000
        self.start_timeout_s = float(start_timeout_s)
        d = differential if isinstance(differential, dict) else ({} if differential else None)
        self.diff_enabled = d is not None
        self.diff_per_query = int((d or {}).get("per_query", 2))
        self.diff_exclude = set((d or {}).get("exclude", []))
        m = metamorphic if isinstance(metamorphic, dict) else ({} if metamorphic else None)
        self.mm_enabled = m is not None
        self.mm_max = int((m or {}).get("max_per_testcase", 6))
        # run each TLP partition on its own and record its row count (vacuity measurement, C3)
        self.measure_partitions = bool((m or {}).get("measure_partitions", False))
        self.max_rows = int(max_rows)
        self.rng = random.Random(seed)
        from pgfuzz.eval.normalize import make as _make_normalizer

        self.normalize = _make_normalizer(normalize)   # cross-engine value normalizers (digests only)
        self.state_check = bool(state_check)
        self._state_base: Any = None
        rf = rule_feedback if isinstance(rule_feedback, dict) else ({} if rule_feedback else None)
        self.rf_enabled = rf is not None
        self.rf_prob = float((rf or {}).get("prob", 0.3))
        # the probe may cost at most this fraction of the time spent executing test cases
        self.rf_overhead = float((rf or {}).get("overhead", 0.25))
        self.rf_seen_plans: set[str] = set()
        # rules that fired in >= 95 % of the first `learn` probes carry no information: not probed later
        self.rf_learn = int((rf or {}).get("learn", 40))
        self.rf_counts: dict[str, int] = {}
        self.rf_ubiquitous: set[str] = set()
        self.rf_stats = {"probed": 0, "skipped_known_plan": 0, "skipped_budget": 0, "probe_ms": 0.0, "exec_ms": 0.0}
        self.proc: Any = None
        self.pipe: Any = None
        self.version: str | None = None
        self.rule_names: list[str] = []
        self.variant_names: list[str] = []
        self.variant_sql: dict[str, list[str]] = {}
        self.aborts = True
        self._oids = load_driver(driver, self.driver_params).type_oids if driver else {}
        self._sqlstate = load_driver(driver, self.driver_params).sqlstate if driver else {}
        self.diff_stats: dict[str, Any] = {"checked": 0, "variant_runs": 0}

    # ------------------------------------------------------------------ worker lifecycle
    def start(self) -> None:
        self._spawn()
        r = self._call(("meta",))
        if r and r[0] == "ok":
            self.rule_names = r[1]["rules"]
            self.variant_names = [v for v in r[1]["variants"] if v not in self.diff_exclude]
            self.variant_sql = r[1]["variant_sql"]
            self.aborts = r[1]["aborts"]

    def stop(self) -> None:
        p = getattr(self, "_stderr_path", None)
        if p:
            import os

            try:
                os.unlink(p)
            except OSError:
                pass
            self._stderr_path = None
        if self.proc is not None:
            try:
                self.pipe.send(("quit",))
            except Exception:
                pass
            self.proc.join(timeout=2)
            if self.proc.is_alive():
                self.proc.kill()
                self.proc.join(timeout=2)
        self.proc = None

    def _spawn(self) -> None:
        ctx = mp.get_context("spawn")
        parent, child = ctx.Pipe()
        if not getattr(self, "_stderr_path", None):
            import tempfile

            self._stderr_path = tempfile.mkstemp(prefix=f"pgfuzz-{self.name}-", suffix=".stderr")[1]
        self.proc = ctx.Process(target=_worker, args=(child, self.driver_path, self.driver_params, self.setup_sql,
                                                      self._stderr_path), daemon=True)
        self.proc.start()
        child.close()
        self.pipe = parent
        if not parent.poll(self.start_timeout_s):
            self.proc.kill()
            raise RuntimeError(f"{self.name} worker did not start")
        msg = parent.recv()
        if msg[0] != "ready":
            raise RuntimeError(f"{self.name} setup failed: {msg[1]}")
        self.version = msg[1]

    def _call(self, msg: tuple) -> tuple | None:
        """Send one request; None if the worker died (crash), ("timeout",) if it was killed."""
        try:
            self.pipe.send(msg)
        except (BrokenPipeError, OSError):
            return None
        if self.pipe.poll(self.timeout_s):
            try:
                return self.pipe.recv()
            except EOFError:
                self.proc.join(timeout=2)
                return None
        if not self.proc.is_alive():
            return None
        self.proc.kill()
        self.proc.join(timeout=2)
        return ("timeout",)

    def _result(self, r: tuple | None) -> dict[str, Any]:
        if r is None:
            code = self.proc.exitcode if self.proc is not None else None
            msg = f"{self.name} worker died (exit code {code})"
            tail = self._stderr_tail()
            if tail:
                msg += "\n" + tail
            return {"status": "connection_lost", "message": msg, "exitcode": code}
        if r[0] == "timeout":
            return {"status": "timeout", "sqlstate": "57014", "message": "statement timeout (worker killed)"}
        if r[0] == "error":
            return {"status": "error", "sqlstate": self._sqlstate.get(r[1], Driver.default_sqlstate),
                    "message": f"{r[1]}: {r[2]}", "error_class": r[1]}
        return {"status": "ok", "rows": r[1], "types": r[2]}

    def _stderr_tail(self) -> str:
        """The engine's last panic / assertion / fatal message from the worker's stderr."""
        import re

        p = getattr(self, "_stderr_path", None)
        if not p:
            return ""
        try:
            with open(p, "rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 16384))
                text = f.read().decode("utf-8", "replace")
        except OSError:
            return ""
        m = None
        for m in re.finditer(r"(panicked at [^\n]*\n[^\n]*|Assertion[^\n]*failed[^\n]*|INTERNAL Error[^\n]*|"
                             r"FATAL[^\n]*|Segmentation fault[^\n]*)", text):
            pass
        return m.group(1)[:600] if m else ""

    def _exec(self, sql: str, fetch: bool = True) -> dict[str, Any]:
        return self._result(self._call(("exec", sql, fetch, self.max_rows)))

    def _op(self, *msg: Any) -> dict[str, Any]:
        return self._result(self._call(tuple(msg)))

    def _alive(self) -> bool:
        return self.proc is not None and self.proc.is_alive()

    def _oid(self, type_name: str) -> int:
        for k, v in self._oids.items():
            if type_name.upper().startswith(k):
                return v
        return 0

    def _digest(self, res: dict[str, Any], sql: str, mask: bool | None = None) -> tuple[str | None, int]:
        """Digest of a result. ``mask`` (float rounding) defaults to what the statement's text calls
        for; the two sides of a metamorphic check must use the same decision (one shared value)."""
        rows = res.get("rows")
        if rows is None:
            return None, 0
        if self.normalize is not None:
            rows = self.normalize(rows)
        if mask is None:
            mask = diff.masks_floats(sql)
        return diff.result_digest(rows, [self._oid(t) for t in res.get("types") or []], mask, self.max_rows)

    # ------------------------------------------------------------------ public helpers (oracles, C1)
    def explain(self, sql: str) -> str | None:
        r = self._op("explain", sql)
        return r["rows"] if r["status"] == "ok" else None

    def run_rows(self, statements: list[str], query: str, limit: int = 30) -> dict[str, Any]:
        """Run ``statements`` then ``query`` in one isolated test case; text rows (triage reports)."""
        if not self._alive():
            self._spawn()
        self._op("begin")
        for s in statements:
            r = self._exec(s, fetch=False)
            if r["status"] in ("connection_lost", "timeout"):
                self._spawn()
                return {"error": r.get("message")}
        r = self._exec(query)
        if self._alive():
            self._op("end")
        else:
            self._spawn()
        if r["status"] != "ok":
            return {"error": f"{r.get('sqlstate', '')} {r.get('message', '')}".strip()}
        rows = r["rows"] or []
        return {"columns": [], "rows": [list(x) for x in rows[:limit]], "row_count": len(rows)}

    def run_variant(self, name: str, sql: str) -> dict[str, Any]:
        """Run ``sql`` under plan variant ``name`` (outside any test case)."""
        self._op("variant", name)
        res = self._exec(sql)
        if self._alive():
            self._op("reset_variant")
        return res

    # ------------------------------------------------------------------ test cases
    def execute(self, testcase: TestCase) -> ExecResult:
        t0 = time.perf_counter()
        if not self._alive():
            self._spawn()
        results: list[StatementResult] = []
        done: list[str] = []
        lost = False
        checks_by_stmt: dict[int, list[dict[str, Any]]] = {}
        if self.mm_enabled:
            for c in (testcase.meta.get("checks") or [])[: self.mm_max]:
                checks_by_stmt.setdefault(int(c.get("stmt", -1)), []).append(c)
        self._op("begin")
        for idx, sql in enumerate(testcase.statements):
            if lost:
                results.append(StatementResult(StatementStatus.SKIPPED))
                continue
            s0 = time.perf_counter()
            res = self._exec(sql)
            if res["status"] == "connection_lost":
                lost = True
                results.append(StatementResult(StatementStatus.CONNECTION_LOST, None, res["message"], _ms(s0)))
                continue
            if res["status"] != "ok":
                results.append(StatementResult(StatementStatus.ERROR, res.get("sqlstate"), res.get("message"), _ms(s0)))
                self._recover(done, res["status"] == "timeout")
                continue
            h, n = self._digest(res, sql) if diff.eligible(sql) else (None, len(res["rows"] or []))
            st = StatementResult(StatementStatus.OK, duration_ms=_ms(s0), rows=n, result_hash=h)
            results.append(st)
            done.append(sql)
            if h is not None and self.diff_enabled and self.variant_names:
                st.variants = self._run_variants(sql, done)
                if any(v["status"] == "connection_lost" for v in st.variants.values()):
                    st.status, lost = StatementStatus.CONNECTION_LOST, True
                    st.message = f"{self.name} worker died while running a plan variant"
            if not lost and self.rf_enabled and h is not None and self.rule_names and self.rng.random() < self.rf_prob:
                self._probe_rules(sql, st)
            if not lost and checks_by_stmt.get(idx) and res["rows"] is not None:
                st.checks = self._run_checks(sql, res, checks_by_stmt[idx], done)
                if any(c.get("status") == "connection_lost" for c in st.checks):
                    st.status, lost = StatementStatus.CONNECTION_LOST, True
                    st.message = f"{self.name} worker died while running a metamorphic check"
        if self.rf_enabled:
            self.rf_stats["exec_ms"] += _ms(t0)
        restarted = False
        if lost or not self._alive():
            self._spawn()
            restarted = True
        else:
            self._op("end")
            self._check_state(testcase, results)
        return ExecResult(results, wall_ms=_ms(t0), server_log=[], server_restarted=restarted,
                          extra={f"{self.name}_version": self.version})

    def _check_state(self, testcase: TestCase, results: list[StatementResult]) -> None:
        """State-restoration oracle: a rolled-back test case must leave the database as it was.
        Only test cases with a statement that can write are checked. A violation is reported as
        a failed check on the last successful statement, and the worker is restarted so that
        the leaked state cannot corrupt later comparisons."""
        if not self.state_check or all(diff.StmtView.of(s).kind in ("SELECT", "VALUES", "TABLE", "EXPLAIN")
                                       for s in testcase.statements):
            return
        if self._state_base is None:                 # first use: the baseline of a fresh worker
            self._spawn()
            r = self._op("state")
            self._state_base = r["rows"] if r["status"] == "ok" else False
            if not self._state_base:
                self.state_check = False              # the driver has no fingerprint
            return                                    # (this one test case goes unchecked)
        r = self._op("state")
        if r["status"] != "ok" or r["rows"] == self._state_base:
            return
        self.diff_stats["state_leaks"] = self.diff_stats.get("state_leaks", 0) + 1
        before, after = set(str(self._state_base).split()), set(str(r["rows"]).split())
        change = f"before: {' '.join(sorted(before - after))}; after ROLLBACK: {' '.join(sorted(after - before))}"
        ok = [st for st in results if st.status is StatementStatus.OK]
        if ok:
            ok[-1].checks = (ok[-1].checks or []) + [{
                "kind": "state_restore", "status": "ok", "confirmed": True, "lhs_hash": "before", "rhs_hash": "after",
                "lhs_rows": len(before - after), "rhs_rows": len(after - before),
                "lhs_sql": "-- database state before the test case", "rhs_sql": f"-- {change}"}]
        self._spawn()

    def _probe_rules(self, sql: str, st: StatementResult) -> None:
        """Fill ``st.plan_shape`` and ``st.rules`` (rule-firing probe). A plan seen before gets
        its shape only: the same plan almost always fires the same rules, and probing costs one
        EXPLAIN per rule."""
        import hashlib

        if self.rf_stats["probe_ms"] > self.rf_overhead * max(self.rf_stats["exec_ms"], 1.0):
            self.rf_stats["skipped_budget"] += 1
            return
        t0 = time.perf_counter()
        plan = self._op("explain", sql)
        if plan["status"] != "ok" or plan["rows"] is None:
            return
        shape = hashlib.sha1(str(plan["rows"]).encode()).hexdigest()[:12]
        st.plan_shape = shape
        if shape in self.rf_seen_plans:
            self.rf_stats["skipped_known_plan"] += 1
            return
        probe = [x for x in self.rule_names if x not in self.rf_ubiquitous]
        r = self._op("fired", sql, probe)
        if r["status"] == "ok":
            self.rf_seen_plans.add(shape)
            st.rules = sorted(r["rows"]["rules"])
            self.rf_stats["probed"] += 1
            for x in st.rules:
                self.rf_counts[x] = self.rf_counts.get(x, 0) + 1
            if self.rf_stats["probed"] == self.rf_learn:
                self.rf_ubiquitous = {x for x, c in self.rf_counts.items() if c >= 0.95 * self.rf_learn}
                self.rf_stats["ubiquitous"] = sorted(self.rf_ubiquitous)
            self.rf_stats["explains"] = self.rf_stats.get("explains", 0) + int(r["rows"].get("explains", 0))
        self.rf_stats["probe_ms"] += (time.perf_counter() - t0) * 1000
        self.diff_stats.update({f"rule_{k}": round(v, 1) if isinstance(v, float) else v
                                for k, v in self.rf_stats.items()})

    def _recover(self, done: list[str], killed: bool = False) -> None:
        """After an error: restore the test case's state (rollback + replay, or respawn)."""
        if killed or not self._alive():
            self._spawn()
        elif not self.aborts:
            return
        else:
            r = self._op("end")
            if r["status"] in ("connection_lost", "timeout") or not self._alive():
                self._spawn()
        self._op("begin")
        for s in done:
            self._exec(s, fetch=False)

    # ------------------------------------------------------------------ oracles
    def _run_variants(self, sql: str, done: list[str]) -> dict[str, dict[str, Any]]:
        self.diff_stats["checked"] += 1
        out: dict[str, dict[str, Any]] = {}
        for name in self.rng.sample(self.variant_names, min(self.diff_per_query, len(self.variant_names))):
            self.diff_stats["variant_runs"] += 1
            rec: dict[str, Any] = {"settings": {"variant": name, "sql": self.variant_sql.get(name, [])}}
            self._op("variant", name)
            res = self._exec(sql)
            if self._alive():
                self._op("reset_variant")
            if res["status"] == "ok":
                h, n = self._digest(res, sql)
                rec.update(status="ok", hash=h, rows=n)
            elif res["status"] == "connection_lost":
                rec.update(status="connection_lost", message=res["message"])
                out[name] = rec
                return out
            else:
                rec.update(status=res["status"], sqlstate=res.get("sqlstate"), message=res.get("message"))
                self._recover(done, res["status"] == "timeout")
            out[name] = rec
        return out

    def _side(self, sql: str, done: list[str], mask: bool | None = None) -> dict[str, Any]:
        res = self._exec(sql)
        if res["status"] == "ok":
            h, n = self._digest(res, sql, mask)
            return {"status": "ok", "hash": h, "rows": n}
        if res["status"] != "connection_lost":
            self._recover(done, res["status"] == "timeout")
        return res

    def _run_checks(self, sql: str, first: dict[str, Any], checks: list[dict[str, Any]],
                    done: list[str]) -> list[dict[str, Any]]:
        out = []
        for c in checks:
            kind, lhs, rhs = str(c.get("kind")), c.get("lhs"), str(c.get("rhs"))
            rec: dict[str, Any] = {"kind": kind}
            if kind in ("cert", "rls"):   # need EXPLAIN estimates / roles: PostgreSQL only
                continue
            # one masking decision for both sides (as the PostgreSQL executor): the generator's flag,
            # or the original statement's text; never per side (a rewrite adding an aggregate would
            # mask floats on one side only)
            mask = bool(c.get("mask")) or diff.masks_floats(sql)
            if lhs is None:
                h, n = self._digest(first, sql, mask)
                left = {"status": "ok", "hash": h, "rows": n}
            else:
                left = self._side(lhs, done, mask)
            right = self._side(rhs, done, mask) if left["status"] == "ok" else {"status": "skipped"}
            failed = left if left["status"] != "ok" else right if right["status"] not in ("ok", "skipped") else None
            if failed is not None:
                side = "lhs" if failed is left else "rhs"
                rec.update(status=failed["status"], side=side, sqlstate=failed.get("sqlstate"),
                           message=failed.get("message"), sql=lhs if side == "lhs" else rhs)
                out.append(rec)
                if failed["status"] == "connection_lost":
                    return out
                continue
            rec.update(status="ok", lhs_hash=left["hash"], rhs_hash=right["hash"],
                       lhs_rows=left["rows"], rhs_rows=right["rows"])
            if self.measure_partitions and c.get("arms"):
                sides = [self._side(str(a), done, mask) for a in c["arms"]]
                rec["partitions"] = [x.get("rows") if x.get("status") == "ok" else None for x in sides]
            if left["hash"] and right["hash"] and left["hash"] != right["hash"]:
                rec.update(lhs_sql=lhs, rhs_sql=rhs)
                l2 = self._side(lhs if lhs is not None else sql, done, mask)
                r2 = self._side(rhs, done, mask)
                rec["confirmed"] = l2.get("hash") == left["hash"] and r2.get("hash") == right["hash"]
            out.append(rec)
        return out

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "driver": self.driver_path, "version": self.version,
                "rules": self.rule_names, "variants": self.variant_names, "timeout_s": self.timeout_s}


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def _load_sql(v: list[str] | str | None) -> list[str]:
    from pgfuzz.core.sqlsplit import split_statements

    if not v:
        return []
    out: list[str] = []
    for p in [v] if isinstance(v, str) else v:
        out += split_statements(Path(p).read_text(encoding="utf-8"))
    return out
