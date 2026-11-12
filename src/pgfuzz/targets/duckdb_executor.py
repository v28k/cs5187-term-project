"""DuckDB target (in-memory database inside a crash-isolated worker; see pgfuzz.targets.base).

Rules = the passes in ``duckdb_optimizers()``; a rule is switched off with
``SET disabled_optimizers``. Extra plan variants: the whole optimizer off and a
single-threaded run. DuckDB has no savepoints, so after an error the executor rolls the
test case's transaction back and replays the statements that succeeded.
"""

from __future__ import annotations

import re
from typing import Any

from pgfuzz.targets.base import Driver, WorkerExecutor

_SQLSTATE = {
    "InternalException": "XX000", "InternalLikeException": "XX000", "FatalException": "XX000", "InvalidInputException": "22023",
    "ParserException": "42601", "SyntaxException": "42601", "BinderException": "42703",
    "CatalogException": "42P01", "ConversionException": "22P02", "OutOfRangeException": "22003",
    "NotImplementedException": "0A000", "TypeMismatchException": "42804", "ConstraintException": "23000",
    "TransactionException": "25000", "OutOfMemoryException": "53200", "InterruptException": "57014",
    "DependencyException": "2BP01", "SequenceException": "22000", "SerializationException": "22000",
    "PermissionException": "42501", "IOException": "58030", "HTTPException": "58030",
}
# passes that are not optimizations (switching them off breaks plans or is meaningless)
_NOT_RULES = {"expression_rewriter"}
# messages of non-internal exception classes that still mean "the engine broke on a valid query"
_INTERNAL_LIKE = ("Cannot copy Bound", "Cannot copy Expanded", "Unimplemented type for", "Attempted to access index",
                  "INTERNAL Error", "Unsupported expression class", "not implemented for type")
_EST = re.compile(r"~\s*[\d,.]+\s*(rows|row)?", re.I)


class DuckDBDriver(Driver):
    name = "duckdb"
    state_tables_sql = ("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' "
                        "AND table_schema = 'main'")
    sqlstate = _SQLSTATE

    def connect(self, setup: list[str]) -> str:
        path = self.params.get("path")
        if path:   # another DuckDB build (pip install --target <path> duckdb==X), e.g. the last release
            import sys

            sys.path.insert(0, str(path))
        import duckdb

        self._duckdb = duckdb
        self.threads = int(self.params.get("threads", 2))
        self.db = duckdb.connect(":memory:", config={"threads": self.threads})
        for s in setup:
            self.db.execute(s)
        self._rules = [r[0] for r in self.db.execute("SELECT name FROM duckdb_optimizers()").fetchall()
                       if r[0] not in _NOT_RULES]
        return duckdb.__version__

    def close(self) -> None:
        self.db.close()

    def execute(self, sql: str, fetch: bool, max_rows: int) -> tuple[list[tuple] | None, list[str] | None]:
        rel = self.db.execute(sql)
        if fetch and rel.description is not None:
            rows = rel.fetchmany(max_rows + 1)
            return rows, [str(d[1]) for d in rel.description]
        return None, None

    def error_name(self, exc: BaseException) -> str | None:
        if not isinstance(exc, self._duckdb.Error):
            return None
        name = type(exc).__name__
        if name == "SerializationException" and any(m in str(exc) for m in _INTERNAL_LIKE):
            return "InternalLikeException"   # e.g. "Cannot copy BoundSubqueryExpression" on a valid query
        return name

    # settings a test case may change (overlays/duckdb.pgg set_stmt); they survive ROLLBACK
    _SESSION_RESET = ("PRAGMA enable_optimizer", "RESET disabled_optimizers", "RESET default_null_order",
                      "RESET preserve_insertion_order")

    def end(self) -> None:
        try:
            self.db.execute("ROLLBACK")
        except self._duckdb.Error:
            pass
        for s in self._SESSION_RESET:
            self.db.execute(s)
        self.db.execute(f"SET threads = {self.threads}")

    def rules(self) -> list[str]:
        return list(self._rules)

    def variants(self) -> dict[str, Any]:
        v: dict[str, Any] = {"no_optimizer": {"sql": ["PRAGMA disable_optimizer"]},
                             "single_thread": {"sql": ["SET threads = 1"]}}
        for r in self._rules:
            v[f"no_{r}"] = {"rules_off": [r]}
        return v

    def _disabled(self) -> str:
        try:
            v = self.db.execute("SELECT current_setting('disabled_optimizers')").fetchone()[0]
        except self._duckdb.Error:
            return ""
        return str(v or "")

    def apply_variant(self, spec: Any) -> None:
        self._applied = spec
        # A test case may itself have run SET disabled_optimizers (the grammar can generate it).
        # Switching a rule off must add to that setting, not replace it: replacing it switches
        # the test case's own rules back on, and then every rule looks as if it fired.
        self._prev_disabled = self._disabled()
        for s in spec.get("sql", []):
            self.db.execute(s)
        if spec.get("rules_off"):
            have = [r.strip() for r in self._prev_disabled.split(",") if r.strip()]
            rules = have + [r for r in spec["rules_off"] if r not in have]
            self.db.execute("SET disabled_optimizers = '" + ",".join(rules) + "'")

    def variant_sql(self, spec: Any) -> list[str]:
        out = list(spec.get("sql", []))
        if spec.get("rules_off"):
            out.append("SET disabled_optimizers = '" + ",".join(spec["rules_off"]) + "'")
        return out

    def reset_variant(self) -> None:
        spec = getattr(self, "_applied", None)
        prev = getattr(self, "_prev_disabled", "")
        restore = f"SET disabled_optimizers = '{prev}'" if prev else "RESET disabled_optimizers"
        if spec is not None and not spec.get("sql"):
            self.db.execute(restore)    # only a rule was switched off
        else:
            for s in ("PRAGMA enable_optimizer", restore, f"SET threads = {self.threads}"):
                self.db.execute(s)
        self._applied = None
        self._prev_disabled = ""

    def explain(self, sql: str) -> str:
        rows = self.db.execute("EXPLAIN " + sql).fetchall()
        text = "\n".join(str(r[1]) for r in rows)
        return _EST.sub("", text)


class DuckDBExecutor(WorkerExecutor):
    """Config-compatible wrapper: ``threads`` and the shared WorkerExecutor options."""

    name = "duckdb"

    def __init__(self, threads: int = 2, path: str | None = None, **kw: Any) -> None:
        params: dict[str, Any] = {"threads": threads}
        if path:
            params["path"] = path
        kw.pop("driver", None)
        super().__init__(driver="pgfuzz.targets.duckdb_executor:DuckDBDriver", driver_params=params, **kw)
