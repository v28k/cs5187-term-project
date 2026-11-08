"""Apache DataFusion target (Python bindings ``datafusion``; see pgfuzz.targets.base).

* Isolation: DataFusion has no transactions, so every test case runs in a fresh
  ``SessionContext`` built from the setup statements (in-memory tables).
* Rule firing comes for free: ``EXPLAIN VERBOSE`` prints the plan after every logical and
  physical optimizer rule, and prints ``SAME TEXT AS ABOVE`` when a rule changed nothing. So
  :meth:`DataFusionDriver.fired` needs one EXPLAIN instead of one per rule.
* Plan variants are configuration switches (``SET datafusion.optimizer...``), e.g. sort-merge
  instead of hash join, no repartitioning, one target partition, no dynamic filters.
* DataFusion marks its own bugs: "Internal error: ... This issue was likely caused by a bug in
  DataFusion's code" -> internal error; a Rust panic surfaces as ``PanicException``.
"""

from __future__ import annotations

import re
from typing import Any

from pgfuzz.targets.base import Driver, WorkerExecutor

_KIND = [  # message prefix -> pseudo error class
    ("Internal error", "InternalError"), ("This feature is not implemented", "NotImplemented"),
    ("SQL error", "ParserError"), ("Error during planning", "PlanError"), ("Schema error", "SchemaError"),
    ("Arrow error", "ArrowError"), ("Execution error", "ExecutionError"), ("Optimizer rule", "OptimizerError"),
    ("Resources exhausted", "ResourcesExhausted"), ("External error", "ExternalError"),
    ("Invalid argument error", "InvalidArgument"), ("Context error", "ContextError"),
]
_SQLSTATE = {
    "InternalError": "XX000", "PanicException": "XX000", "NotImplemented": "0A000", "ParserError": "42601",
    "PlanError": "42703", "SchemaError": "42P01", "ArrowError": "22000", "ExecutionError": "22000",
    "OptimizerError": "22000", "ResourcesExhausted": "53200", "ExternalError": "58030",
    "InvalidArgument": "22023", "ContextError": "42P01",
}
# configuration switches used as plan variants
_VARIANTS = {
    "sort_merge_join": "SET datafusion.optimizer.prefer_hash_join = false",
    "one_partition": "SET datafusion.execution.target_partitions = 1",
    "no_repartition_joins": "SET datafusion.optimizer.repartition_joins = false",
    "no_repartition_aggregations": "SET datafusion.optimizer.repartition_aggregations = false",
    "no_round_robin": "SET datafusion.optimizer.enable_round_robin_repartition = false",
    "no_topk_aggregation": "SET datafusion.optimizer.enable_topk_aggregation = false",
    "no_dynamic_filters": "SET datafusion.optimizer.enable_dynamic_filter_pushdown = false",
    "no_filter_null_join_keys": "SET datafusion.optimizer.filter_null_join_keys = false",
    "small_batches": "SET datafusion.execution.batch_size = 2",
    "no_coalesce_batches": "SET datafusion.execution.coalesce_batches = false",
}
_AFTER = re.compile(r"^(logical_plan|physical_plan) after (\S+)")


class DataFusionDriver(Driver):
    name = "datafusion"
    sqlstate = _SQLSTATE
    error_aborts_transaction = False
    type_oids = {"FLOAT64": 701, "FLOAT32": 700, "DECIMAL": 1700, "INTERVAL": 1186, "DOUBLE": 701, "FLOAT": 700}

    def connect(self, setup: list[str]) -> str:
        import datafusion

        self._df = datafusion
        self.setup = list(setup)
        self.partitions = int(self.params.get("target_partitions", 4))
        self._rules: list[str] = []
        self._fresh()
        d = self.ctx.sql("SELECT name, value FROM information_schema.df_settings").collect()
        self._defaults = {}
        for b in d:
            x = b.to_pydict()
            self._defaults.update(zip(x["name"], x["value"]))
        self._applied: list[str] = []
        self.fired("SELECT 1")                # learn the rule names
        return datafusion.__version__

    def _fresh(self) -> None:
        cfg = self._df.SessionConfig().with_target_partitions(self.partitions).with_information_schema(True)
        self.ctx = self._df.SessionContext(cfg)
        for s in self.setup:
            self.ctx.sql(s).collect()

    def begin(self) -> None:
        self._fresh()

    def end(self) -> None:
        pass

    def execute(self, sql: str, fetch: bool, max_rows: int) -> tuple[list[tuple] | None, list[str] | None]:
        frame = self.ctx.sql(sql)
        batches = frame.collect()
        schema = frame.schema()
        head = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
        if head in ("CREATE", "DROP", "SET", "INSERT", "UPDATE", "DELETE") and not fetch:
            return None, None
        if head in ("CREATE", "DROP", "SET"):
            return None, None
        if not fetch:
            return None, None
        names = [f.name for f in schema]
        types = [str(f.type).upper() for f in schema]
        rows: list[tuple] = []
        for b in batches:
            cols = b.to_pydict()
            for i in range(b.num_rows):
                rows.append(tuple(cols[n][i] for n in names) if len(set(names)) == len(names)
                            else tuple(b.column(k)[i].as_py() for k in range(b.num_columns)))
                if len(rows) > max_rows:
                    return rows, types
        return rows, types

    def error_name(self, exc: BaseException) -> str | None:
        name = type(exc).__name__
        if "Panic" in name:
            return "PanicException"
        msg = str(exc)
        if "likely caused by a bug in DataFusion" in msg or "No field named __common_expr" in msg:
            return "InternalError"
        body = msg.split("DataFusion error:", 1)[-1].strip()
        for prefix, kind in _KIND:
            if body.startswith(prefix) or f"{prefix}:" in body[:200]:
                return kind
        return "ExecutionError"

    # ---------------------------------------------------------------- rules / plans
    def _verbose(self, sql: str) -> list[tuple[str, str]]:
        out = self.ctx.sql("EXPLAIN VERBOSE " + sql).collect()
        rows: list[tuple[str, str]] = []
        for b in out:
            d = b.to_pydict()
            rows += list(zip(d["plan_type"], d["plan"]))
        return rows

    def rules(self) -> list[str]:
        return list(self._rules)

    def variants(self) -> dict[str, Any]:
        return {k: {"sql": [v]} for k, v in _VARIANTS.items()}

    def apply_variant(self, spec: Any) -> None:
        for s in spec.get("sql", []):
            self.ctx.sql(s).collect()
            self._applied.append(s.split()[1])

    def reset_variant(self) -> None:
        """Put switched settings back to their defaults (the session keeps the test case's tables)."""
        for key in self._applied:
            v = self._defaults.get(key)
            if v is not None:
                self.ctx.sql(f"SET {key} = {v}" if v.replace('.', '').isdigit() or v in ('true', 'false')
                             else f"SET {key} = '{v}'").collect()
        self._applied = []

    def explain(self, sql: str) -> str:
        rows = self._verbose(sql)
        final = [p for t, p in rows if t in ("physical_plan", "logical_plan")]
        return "\n".join(final)

    def fired(self, sql: str, rules: list[str] | None = None) -> tuple[str, list[str]]:
        rows = self._verbose(sql)
        out, seen = [], set()
        for t, p in rows:
            m = _AFTER.match(t)
            if not m:
                continue
            kind, rule = m.group(1), m.group(2)
            name = ("L:" if kind == "logical_plan" else "P:") + rule
            if name not in self._rules:
                self._rules.append(name)
            if p.strip() != "SAME TEXT AS ABOVE" and name not in seen and (rules is None or name in rules):
                out.append(name)
                seen.add(name)
        base = "\n".join(p for t, p in rows if t in ("physical_plan", "logical_plan"))
        return base, out


class DataFusionExecutor(WorkerExecutor):
    name = "datafusion"

    def __init__(self, target_partitions: int = 4, **kw: Any) -> None:
        kw.pop("driver", None)
        super().__init__(driver="pgfuzz.targets.datafusion_executor:DataFusionDriver",
                         driver_params={"target_partitions": target_partitions}, **kw)
