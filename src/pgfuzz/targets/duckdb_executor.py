"""DuckDB target: runs test cases in an in-memory DuckDB inside a worker process.

The engine runs in-process, so an abort or a segfault would take the fuzzer down with
it. Each executor therefore owns one worker process (``multiprocessing``, spawn) that
holds the database; the parent talks to it over a pipe. A worker that dies is a crash
(the exit signal is recorded); a worker that does not answer within the statement
timeout is killed and the statement counted as a timeout. A fresh worker reloads the
schema.

Errors map to pseudo SQLSTATEs so the shared oracle (``pgfuzz.eval.oracle``) can
classify them: ``INTERNAL Error`` and ``FATAL Error`` are internal errors (XX000), the
others are syntax, semantic or runtime errors.

Plan variants switch off one DuckDB optimizer pass, or the whole optimizer, or run
single-threaded; a different result under a variant is a wrong-result candidate, as for
PostgreSQL. Metamorphic checks attached by the grammar generator run the same way.
"""

from __future__ import annotations

import multiprocessing as mp
import random
import time
from pathlib import Path
from typing import Any

from pgfuzz.core.interfaces import Executor
from pgfuzz.core.types import ExecResult, StatementResult, StatementStatus, TestCase
from pgfuzz.eval import differential as diff

# DuckDB exception class -> pseudo SQLSTATE understood by pgfuzz.eval.oracle
_SQLSTATE = {
    "InternalException": "XX000", "FatalException": "XX000", "InvalidInputException": "22023",
    "ParserException": "42601", "SyntaxException": "42601", "BinderException": "42703",
    "CatalogException": "42P01", "ConversionException": "22P02", "OutOfRangeException": "22003",
    "NotImplementedException": "0A000", "TypeMismatchException": "42804", "ConstraintException": "23000",
    "TransactionException": "25000", "OutOfMemoryException": "53200", "InterruptException": "57014",
    "DependencyException": "2BP01", "SequenceException": "22000", "SerializationException": "22000",
    "PermissionException": "42501", "IOException": "58030", "HTTPException": "58030",
}
# DuckDB type name prefix -> PostgreSQL type OID used by differential.result_digest
_TYPE_OID = {"DECIMAL": diff.NUMERIC_OID, "DOUBLE": 701, "FLOAT": 700, "INTERVAL": diff.INTERVAL_OID}


def _oid(type_name: str) -> int:
    for k, v in _TYPE_OID.items():
        if type_name.upper().startswith(k):
            return v
    return 0


def _worker(conn: Any, setup: list[str], threads: int) -> None:  # runs in the child process
    import duckdb

    db = duckdb.connect(":memory:", config={"threads": threads})
    for s in setup:
        db.execute(s)
    conn.send(("ready", duckdb.__version__))
    while True:
        try:
            msg = conn.recv()
        except EOFError:
            return
        op = msg[0]
        if op == "quit":
            return
        try:
            if op == "exec":
                _, sql, fetch, max_rows = msg
                rel = db.execute(sql)
                if fetch and rel.description is not None:
                    rows = rel.fetchmany(max_rows + 1)
                    types = [str(d[1]) for d in rel.description]
                    conn.send(("ok", [tuple(str(v) if v is not None else None for v in r) for r in rows], types))
                else:
                    conn.send(("ok", None, None))
            elif op == "optimizers":
                conn.send(("ok", [r[0] for r in db.execute("SELECT name FROM duckdb_optimizers()").fetchall()], None))
        except duckdb.Error as e:
            conn.send(("error", type(e).__name__, str(e)))
        except Exception as e:  # pragma: no cover - client-side problems
            conn.send(("error", "ClientError", f"{type(e).__name__}: {e}"))


class DuckDBExecutor(Executor):
    name = "duckdb"

    def __init__(self, setup_sql: list[str] | str | None = None, statement_timeout_ms: int = 5000,
                 threads: int = 4, differential: bool | dict[str, Any] = False,
                 metamorphic: bool | dict[str, Any] = False, max_rows: int = 10000, seed: int = 0) -> None:
        self.setup_sql = _load_sql(setup_sql)
        self.timeout_s = statement_timeout_ms / 1000
        self.threads = int(threads)
        d = differential if isinstance(differential, dict) else ({} if differential else None)
        self.diff_enabled = d is not None
        self.diff_per_query = int((d or {}).get("per_query", 2))
        m = metamorphic if isinstance(metamorphic, dict) else ({} if metamorphic else None)
        self.mm_enabled = m is not None
        self.mm_max = int((m or {}).get("max_per_testcase", 6))
        self.max_rows = int(max_rows)
        self.rng = random.Random(seed)
        self.proc: Any = None
        self.pipe: Any = None
        self.version = None
        self.optimizers: list[str] = []
        self.diff_stats: dict[str, Any] = {"checked": 0, "variant_runs": 0}

    # ------------------------------------------------------------------ worker lifecycle
    def start(self) -> None:
        self._spawn()
        ok = self._call(("optimizers",))
        self.optimizers = ok[1] if ok and ok[0] == "ok" else []

    def stop(self) -> None:
        if self.proc is not None:
            try:
                self.pipe.send(("quit",))
            except Exception:
                pass
            self.proc.join(timeout=2)
            if self.proc.is_alive():
                self.proc.kill()
        self.proc = None

    def _spawn(self) -> None:
        ctx = mp.get_context("spawn")
        parent, child = ctx.Pipe()
        self.proc = ctx.Process(target=_worker, args=(child, self.setup_sql, self.threads), daemon=True)
        self.proc.start()
        child.close()
        self.pipe = parent
        if not parent.poll(60):
            raise RuntimeError("DuckDB worker did not start")
        _, self.version = parent.recv()

    def _call(self, msg: tuple) -> tuple | None:
        """Send one request; None if the worker died (crash) or timed out (killed)."""
        self.pipe.send(msg)
        if self.pipe.poll(self.timeout_s):
            try:
                return self.pipe.recv()
            except EOFError:
                return None
        if not self.proc.is_alive():
            return None
        self.proc.kill()
        self.proc.join(timeout=2)
        return ("timeout",)

    def _exec(self, sql: str, fetch: bool = True) -> dict[str, Any]:
        r = self._call(("exec", sql, fetch, self.max_rows))
        if r is None:
            code = self.proc.exitcode if self.proc is not None else None
            return {"status": "connection_lost", "message": f"DuckDB worker died (exit code {code})", "exitcode": code}
        if r[0] == "timeout":
            return {"status": "timeout", "sqlstate": "57014", "message": "statement timeout (worker killed)"}
        if r[0] == "error":
            return {"status": "error", "sqlstate": _SQLSTATE.get(r[1], "22000"), "message": f"{r[1]}: {r[2]}"}
        return {"status": "ok", "rows": r[1], "types": r[2]}

    def _digest(self, res: dict[str, Any], sql: str) -> tuple[str | None, int]:
        rows = res.get("rows")
        if rows is None:
            return None, 0
        return diff.result_digest(rows, [_oid(t) for t in res.get("types") or []], diff.masks_floats(sql), self.max_rows)

    def _restart(self) -> None:
        self.stop()
        self._spawn()

    # ------------------------------------------------------------------ test cases
    def execute(self, testcase: TestCase) -> ExecResult:
        t0 = time.perf_counter()
        if self.proc is None or not self.proc.is_alive():
            self._spawn()
        results: list[StatementResult] = []
        done: list[str] = []
        lost = False
        checks_by_stmt: dict[int, list[dict[str, Any]]] = {}
        if self.mm_enabled:
            for c in (testcase.meta.get("checks") or [])[: self.mm_max]:
                checks_by_stmt.setdefault(int(c.get("stmt", -1)), []).append(c)
        self._exec("BEGIN TRANSACTION", fetch=False)
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
                self._recover(done)
                continue
            h, n = self._digest(res, sql) if diff.eligible(sql) else (None, len(res["rows"] or []))
            st = StatementResult(StatementStatus.OK, duration_ms=_ms(s0), rows=n, result_hash=h)
            results.append(st)
            done.append(sql)
            if h is not None and self.diff_enabled:
                st.variants = self._run_variants(sql, done)
                if any(v["status"] == "connection_lost" for v in st.variants.values()):
                    st.status, lost = StatementStatus.CONNECTION_LOST, True
                    st.message = "DuckDB worker died while running a plan variant"
            if not lost and checks_by_stmt.get(idx) and res["rows"] is not None:
                st.checks = self._run_checks(sql, res, checks_by_stmt[idx], done)
                if any(c.get("status") == "connection_lost" for c in st.checks):
                    st.status, lost = StatementStatus.CONNECTION_LOST, True
                    st.message = "DuckDB worker died while running a metamorphic check"
        restarted = False
        if lost:
            self._spawn()
            restarted = True
        else:
            self._exec("ROLLBACK", fetch=False)
        return ExecResult(results, wall_ms=_ms(t0), server_log=[], server_restarted=restarted,
                          extra={"duckdb_version": self.version})

    def _recover(self, done: list[str]) -> None:
        """After an error the transaction is aborted: roll back and replay what succeeded."""
        r = self._exec("ROLLBACK", fetch=False)
        if r["status"] in ("connection_lost", "timeout") or (self.proc is not None and not self.proc.is_alive()):
            self._spawn()
        self._exec("BEGIN TRANSACTION", fetch=False)
        for s in done:
            self._exec(s, fetch=False)

    # ------------------------------------------------------------------ oracles
    def variants(self) -> dict[str, list[str]]:
        v = {"no_optimizer": ["PRAGMA disable_optimizer"], "single_thread": ["SET threads = 1"]}
        for name in self.optimizers:
            if name not in ("expression_rewriter",):
                v[f"no_{name}"] = [f"SET disabled_optimizers = '{name}'"]
        return v

    _RESET = ["PRAGMA enable_optimizer", "RESET disabled_optimizers", "RESET threads"]

    def _run_variants(self, sql: str, done: list[str]) -> dict[str, dict[str, Any]]:
        self.diff_stats["checked"] += 1
        allv = self.variants()
        out: dict[str, dict[str, Any]] = {}
        for name in self.rng.sample(sorted(allv), min(self.diff_per_query, len(allv))):
            self.diff_stats["variant_runs"] += 1
            rec: dict[str, Any] = {"settings": {"sql": "; ".join(allv[name])}}
            for s in allv[name]:
                self._exec(s, fetch=False)
            res = self._exec(sql)
            for s in self._RESET:
                self._exec(s, fetch=False)
            if res["status"] == "ok":
                h, n = self._digest(res, sql)
                rec.update(status="ok", hash=h, rows=n)
            elif res["status"] == "connection_lost":
                rec.update(status="connection_lost", message=res["message"])
                out[name] = rec
                return out
            else:
                rec.update(status="error" if res["status"] == "error" else res["status"],
                           sqlstate=res.get("sqlstate"), message=res.get("message"))
                self._recover(done)
            out[name] = rec
        return out

    def _side(self, sql: str, done: list[str]) -> dict[str, Any]:
        res = self._exec(sql)
        if res["status"] == "ok":
            h, n = self._digest(res, sql)
            return {"status": "ok", "hash": h, "rows": n}
        if res["status"] != "connection_lost":
            self._recover(done)
        return res

    def _run_checks(self, sql: str, first: dict[str, Any], checks: list[dict[str, Any]], done: list[str]) -> list[dict[str, Any]]:
        out = []
        for c in checks:
            kind, lhs, rhs = str(c.get("kind")), c.get("lhs"), str(c.get("rhs"))
            rec: dict[str, Any] = {"kind": kind}
            if kind in ("cert", "rls"):   # need EXPLAIN estimates / roles: PostgreSQL only
                continue
            if lhs is None:
                h, n = self._digest(first, sql)
                left = {"status": "ok", "hash": h, "rows": n}
            else:
                left = self._side(lhs, done)
            right = self._side(rhs, done) if left["status"] == "ok" else {"status": "skipped"}
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
            if left["hash"] and right["hash"] and left["hash"] != right["hash"]:
                rec.update(lhs_sql=lhs, rhs_sql=rhs)
                l2 = self._side(lhs if lhs is not None else sql, done)
                r2 = self._side(rhs, done)
                rec["confirmed"] = l2.get("hash") == left["hash"] and r2.get("hash") == right["hash"]
            out.append(rec)
        return out

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version, "threads": self.threads,
                "variants": sorted(self.variants()) if self.optimizers else [], "timeout_s": self.timeout_s}


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
