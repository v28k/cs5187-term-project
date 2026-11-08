"""SQLite target through APSW (bundles the newest SQLite release; see pgfuzz.targets.base).

Rules = the query-planner optimizations that ``sqlite3_test_control(SQLITE_TESTCTRL_OPTIMIZATIONS,
db, mask)`` can switch off (the same switches SQLite's own SLT runs use). APSW links SQLite
statically and does not export that function, so the driver locates it through the
module's ELF symbol table (``nm``) and calls it by address; if that is not possible the
target still works, only without rule variants.

An error in SQLite rolls back the statement, not the transaction, so no replay is needed.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
from typing import Any

from pgfuzz.targets.base import Driver, WorkerExecutor

SQLITE_TESTCTRL_OPTIMIZATIONS = 15
# sqliteInt.h (trunk 2026-11): bit numbers of dbOptFlags; mask = 1 << (n - 1)
OPT_BITS = {
    "QueryFlattener": 1, "WindowFunc": 2, "GroupByOrder": 3, "JoinMiss": 4, "DistinctOpt": 5, "CoverIdxScan": 6,
    "OrderByIdxJoin": 7, "Transitive": 8, "OmitNoopJoin": 9, "CountOfView": 10, "Stat4": 12,
    "PushDown": 13, "SimplifyJoin": 14, "SkipScan": 15, "PropagateConst": 16, "MinMaxOpt": 17, "SeekScan": 18,
    "OmitOrderBy": 19, "BloomFilter": 20, "BalancedMerge": 22, "FlttnUnionAll": 24, "IndexedExpr": 25,
    "Coroutines": 26, "NullUnusedCols": 27, "OnePass": 28, "OrderBySubq": 29, "StarQuery": 30,
    "ExistsToJoin": 31, "UnionLimit": 32, "HavingToWhere": 33,
}
# not optimizations for testing purposes (CursorHints 11, DevTest 21, ReleaseReg 23)

_SQLSTATE = {
    "SQLError": "42601", "ConstraintError": "23000", "MismatchError": "42804", "RangeError": "22003",
    "TooBigError": "54000", "InternalError": "XX000", "CorruptError": "XX001", "NoMemError": "53200",
    "AbortError": "57014", "InterruptError": "57014", "BusyError": "55P03", "LockedError": "55P03",
    "ReadOnlyError": "25006", "SchemaChangeError": "XX000", "ExecutionCompleteError": "XX000",
    "ThreadingViolationError": "XX000", "CursorClosedError": "XX000", "ConnectionClosedError": "XX000",
    "BindingsError": "42P18", "IncompleteExecutionError": "XX000", "ExecTraceAbort": "XX000",
    "AuthError": "42501", "FormatError": "22000", "NotADBError": "XX001", "ValueError": "22023",
    "TypeError": "42804", "OverflowError": "22003",
}
# SQLite messages that mean "the engine broke", whatever the error class
_INTERNAL_MSGS = ("malformed database schema", "database disk image is malformed", "internal error",
                  "unable to close due to", "SQL logic error")


def _returns_rows(sql: str) -> bool:
    head = sql.lstrip().lstrip("(").split(None, 1)[0].upper() if sql.strip() else ""
    return head in ("SELECT", "WITH", "VALUES", "EXPLAIN", "PRAGMA") or " RETURNING " in f" {sql.upper()} "


def _test_control_function(module_path: str) -> Any | None:
    """Address of the (local) sqlite3_test_control symbol inside the loaded APSW module."""
    try:
        out = subprocess.run(["nm", module_path], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    off = None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == "sqlite3_test_control":
            off = int(parts[0], 16)
            break
    if off is None:
        return None
    real = os.path.realpath(module_path)
    base = None
    with open("/proc/self/maps", encoding="utf-8") as f:
        for line in f:
            fields = line.split()
            if len(fields) >= 6 and os.path.realpath(fields[5]) == real and int(fields[2], 16) == 0:
                base = int(fields[0].split("-")[0], 16)
                break
    if base is None:
        return None
    proto = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint64)
    return proto(base + off)


class SQLiteDriver(Driver):
    name = "sqlite"
    sqlstate = _SQLSTATE
    error_aborts_transaction = False
    type_oids = {"REAL": 701, "FLOAT": 701, "DOUBLE": 701, "NUMERIC": 1700, "DECIMAL": 1700}

    def connect(self, setup: list[str]) -> str:
        import apsw

        self._apsw = apsw
        # no statement cache: a cached statement keeps the plan it was compiled with, so a query
        # re-run under an optimizer switch (plan variants, rule probe) would reuse the old plan
        self.db = apsw.Connection(":memory:", statementcachesize=0)
        for s in setup:
            self._run(s)
        self._tc = _test_control_function(apsw.__file__) if self.params.get("rules", True) else None
        self._rules = sorted(OPT_BITS) if self._tc is not None else []
        return apsw.sqlite_lib_version()

    def _run(self, sql: str) -> list[tuple]:
        return list(self.db.cursor().execute(sql))

    def execute(self, sql: str, fetch: bool, max_rows: int) -> tuple[list[tuple] | None, list[str] | None]:
        cur = self.db.cursor()
        cur.execute(sql)
        try:
            desc = cur.getdescription()
        except self._apsw.ExecutionCompleteError:
            # APSW cannot describe a statement that produced no rows: a query (or DML with
            # RETURNING) that returned nothing is an empty result set, everything else has none
            if _returns_rows(sql):
                return ([], []) if fetch else (None, None)
            return None, None
        rows = []
        for r in cur:
            rows.append(r)
            if len(rows) > max_rows:
                break
        if not fetch:
            return None, None
        # SQLite is dynamically typed: report REAL for columns holding floats (digest masking)
        types = []
        for i, d in enumerate(desc):
            t = (d[1] or "").upper()
            if any(isinstance(r[i], float) for r in rows[:50]):
                t = "REAL"
            types.append(t)
        return rows, types

    def error_name(self, exc: BaseException) -> str | None:
        if not isinstance(exc, (self._apsw.Error, ValueError, TypeError, OverflowError)):
            return None
        if any(m in str(exc) for m in _INTERNAL_MSGS):
            return "InternalError"
        return type(exc).__name__

    def begin(self) -> None:
        self._run("BEGIN")

    def end(self) -> None:
        if not self.db.getautocommit():
            self._run("ROLLBACK")
        for p in ("PRAGMA reverse_unordered_selects = 0", "PRAGMA automatic_index = 1"):
            self._run(p)

    # ---------------------------------------------------------------- rules
    def rules(self) -> list[str]:
        return list(self._rules)

    def variants(self) -> dict[str, Any]:
        v: dict[str, Any] = {f"no_{r}": {"mask": 1 << (OPT_BITS[r] - 1)} for r in self._rules}
        if self._tc is not None:
            v["no_all_optimizations"] = {"mask": (1 << 33) - 1}
        v["reverse_unordered"] = {"sql": ["PRAGMA reverse_unordered_selects = 1"]}
        v["no_automatic_index"] = {"sql": ["PRAGMA automatic_index = 0"]}
        return v

    def rules_off_spec(self, rules: list[str]) -> Any:
        mask = 0
        for r in rules:
            mask |= 1 << (OPT_BITS[r] - 1)
        return {"mask": mask}

    def apply_variant(self, spec: Any) -> None:
        for s in spec.get("sql", []):
            self._run(s)
        if "mask" in spec and self._tc is not None:
            self._tc(SQLITE_TESTCTRL_OPTIMIZATIONS, ctypes.c_void_p(self.db.sqlite3pointer()), spec["mask"])

    def variant_sql(self, spec: Any) -> list[str]:
        out = list(spec.get("sql", []))
        if "mask" in spec:
            out.append(f".testctrl optimizations 0x{spec['mask']:x}")    # sqlite3 shell command
        return out

    def reset_variant(self) -> None:
        if self._tc is not None:
            self._tc(SQLITE_TESTCTRL_OPTIMIZATIONS, ctypes.c_void_p(self.db.sqlite3pointer()), 0)
        for p in ("PRAGMA reverse_unordered_selects = 0", "PRAGMA automatic_index = 1"):
            self._run(p)

    def explain(self, sql: str) -> str:
        rows = self._run("EXPLAIN QUERY PLAN " + sql)
        depth: dict[int, int] = {0: -1}
        lines = []
        for r in rows:
            node, parent, detail = r[0], r[1], r[3]
            depth[node] = depth.get(parent, -1) + 1
            lines.append("  " * depth[node] + str(detail))
        return "\n".join(lines)


class SQLiteExecutor(WorkerExecutor):
    name = "sqlite"

    def __init__(self, rules: bool = True, **kw: Any) -> None:
        kw.pop("driver", None)
        super().__init__(driver="pgfuzz.targets.sqlite_executor:SQLiteDriver", driver_params={"rules": rules}, **kw)
