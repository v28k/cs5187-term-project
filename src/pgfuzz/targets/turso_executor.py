"""Turso target (the SQLite-compatible database written in Rust; Python bindings ``pyturso``).

Turso aims to be a drop-in replacement for SQLite, so its main oracle is differential:
the same test case on Turso and on SQLite (``CrossVersionExecutor`` with this executor as
``test`` and :class:`pgfuzz.targets.sqlite_executor.SQLiteExecutor` as ``reference``), plus
the metamorphic checks. Turso has no optimizer switches yet, so there are no rule variants.

Panics in the Rust code surface as Python exceptions (``InternalError``/``PanicException``)
or kill the worker; both are internal errors.
"""

from __future__ import annotations

from typing import Any

from pgfuzz.targets.base import Driver, WorkerExecutor

_SQLSTATE = {
    "DatabaseError": "42601", "OperationalError": "42601", "ProgrammingError": "42601", "IntegrityError": "23000",
    "DataError": "22000", "NotSupportedError": "0A000", "InterfaceError": "XX000", "InternalError": "XX000",
    "PanicException": "XX000", "InternalLikeError": "XX000",
}
# messages that mean "the engine broke" whatever the exception class
_INTERNAL_MSGS = ("panicked", "Internal error", "internal error", "assertion", "unreachable", "not yet implemented",
                  "Corrupt", "corrupt", "index out of bounds", "called `Option::unwrap()`", "called `Result::unwrap()`")


class TursoDriver(Driver):
    name = "turso"
    sqlstate = _SQLSTATE
    state_tables_sql = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    error_aborts_transaction = False
    type_oids = {"REAL": 701, "FLOAT": 701, "DOUBLE": 701, "NUMERIC": 1700, "DECIMAL": 1700}

    def connect(self, setup: list[str]) -> str:
        path = self.params.get("path")
        if path:
            import sys

            sys.path.insert(0, str(path))
        import turso

        self._turso = turso
        feats = self.params.get("experimental_features", "generated_columns")
        self.db = turso.connect(":memory:", isolation_level=None, experimental_features=feats)
        self.cur = self.db.cursor()
        for s in setup:
            self.cur.execute(s)
        self.cur.execute("SELECT sqlite_version()")
        sv = self.cur.fetchall()[0][0]
        try:
            from importlib.metadata import distributions, version

            ver = version("pyturso")
            if path:
                ds = [d for d in distributions(path=[str(path)]) if d.metadata["Name"] == "pyturso"]
                if ds:
                    ver = ds[0].version
            return f"pyturso {ver} (sqlite_version {sv})"
        except Exception:
            return f"turso (sqlite_version {sv})"

    def execute(self, sql: str, fetch: bool, max_rows: int) -> tuple[list[tuple] | None, list[str] | None]:
        self.cur.execute(sql)
        if self.cur.description is None:
            return None, None
        rows = self.cur.fetchmany(max_rows + 1) if hasattr(self.cur, "fetchmany") else self.cur.fetchall()[: max_rows + 1]
        if not fetch:
            return None, None
        types = []
        for i in range(len(self.cur.description)):
            types.append("REAL" if any(isinstance(r[i], float) for r in rows[:50]) else "")
        return rows, types

    def error_name(self, exc: BaseException) -> str | None:
        name = type(exc).__name__
        if any(m in str(exc) for m in _INTERNAL_MSGS) or "Panic" in name:
            return "InternalLikeError"
        if isinstance(exc, self._turso.Error):
            return name
        return "InternalLikeError"      # any other exception escaping the binding is a bug in it

    def begin(self) -> None:
        self.cur.execute("BEGIN")

    def end(self) -> None:
        try:
            self.cur.execute("ROLLBACK")
        except self._turso.Error:
            pass

    def variants(self) -> dict[str, Any]:
        return {}

    def explain(self, sql: str) -> str:
        self.cur.execute("EXPLAIN QUERY PLAN " + sql)
        return "\n".join(str(r[-1]) for r in self.cur.fetchall())


class TursoExecutor(WorkerExecutor):
    name = "turso"

    def __init__(self, path: str | None = None, experimental_features: str = "generated_columns", **kw: Any) -> None:
        params: dict[str, Any] = {"experimental_features": experimental_features}
        if path:
            params["path"] = path
        kw.pop("driver", None)
        super().__init__(driver="pgfuzz.targets.turso_executor:TursoDriver", driver_params=params, **kw)
