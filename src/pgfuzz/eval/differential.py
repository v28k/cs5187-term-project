"""Differential plan testing: the same query must return the same rows under every
planner setting.

PostgreSQL's planner GUCs (``enable_hashjoin``, ``enable_nestloop``,
``debug_parallel_query``, ``work_mem`` ...) change *how* a query runs, never
*what* it returns. Running a deterministic query once with default settings and
once under a plan variant, and comparing the two result multisets, finds
optimizer and executor logic bugs ("wrong results") that never crash. The
idea is the same as in plan-guided testing tools such as SQLancer's QPG; here
it is applied to every query the generator produces.

The executor runs the variants and records *facts* (a digest of each result,
see :class:`pgfuzz.core.types.StatementResult`); the oracle decides whether a
difference is a bug. To avoid false alarms, only queries whose result is fully
determined by the data are compared (:func:`eligible`), results are compared as
multisets, and float columns are masked when the query aggregates (summation
order legitimately changes the last digits).
"""

from __future__ import annotations

import hashlib
import zlib
from typing import Any, Iterable, Sequence

from pgfuzz.eval.features import StmtView

# name -> settings applied with SET LOCAL. Settings unknown to the server are
# dropped when the executor starts (each variant is probed once).
DEFAULT_VARIANTS: dict[str, dict[str, str]] = {
    "nestloop_only": {"enable_hashjoin": "off", "enable_mergejoin": "off"},
    "hashjoin_only": {"enable_nestloop": "off", "enable_mergejoin": "off"},
    "mergejoin_only": {"enable_nestloop": "off", "enable_hashjoin": "off"},
    "no_hashagg": {"enable_hashagg": "off"},
    "no_sort_opt": {"enable_incremental_sort": "off", "enable_presorted_aggregate": "off"},
    "index_scans": {"enable_seqscan": "off", "enable_bitmapscan": "off"},
    "seq_scans": {"enable_indexscan": "off", "enable_indexonlyscan": "off", "enable_bitmapscan": "off"},
    "no_memoize_material": {"enable_memoize": "off", "enable_material": "off"},
    "parallel": {"debug_parallel_query": "on", "parallel_setup_cost": "0", "parallel_tuple_cost": "0",
                 "min_parallel_table_scan_size": "0", "min_parallel_index_scan_size": "0",
                 "max_parallel_workers_per_gather": "4", "parallel_leader_participation": "off"},
    "partitionwise": {"enable_partitionwise_join": "on", "enable_partitionwise_aggregate": "on"},
    "no_partition_pruning": {"enable_partition_pruning": "off"},
    "geqo": {"geqo": "on", "geqo_threshold": "2"},
    "no_join_reorder": {"join_collapse_limit": "1", "from_collapse_limit": "1"},
    "tiny_work_mem": {"work_mem": "64kB", "hash_mem_multiplier": "1"},
    "no_reordering": {"enable_group_by_reordering": "off", "enable_distinct_reordering": "off"},
    "no_self_join_elim": {"enable_self_join_elimination": "off"},
    "jit": {"jit": "on", "jit_above_cost": "0", "jit_inline_above_cost": "0", "jit_optimize_above_cost": "0"},
}

# Functions whose value is not determined by the data (or that change state).
_VOLATILE = frozenset(
    "RANDOM SETSEED RANDOM_NORMAL CLOCK_TIMESTAMP STATEMENT_TIMESTAMP TIMEOFDAY NEXTVAL CURRVAL SETVAL LASTVAL "
    "GEN_RANDOM_UUID UUIDV4 UUIDV7 UUID_GENERATE_V4 PG_SLEEP PG_SLEEP_FOR PG_SLEEP_UNTIL TXID_CURRENT "
    "PG_CURRENT_XACT_ID TXID_CURRENT_IF_ASSIGNED PG_STAT_GET_ACTIVITY PG_STAT_ACTIVITY PG_BACKEND_PID "
    "PG_CANCEL_BACKEND PG_TERMINATE_BACKEND PG_ADVISORY_LOCK PG_TRY_ADVISORY_LOCK PG_NOTIFY SET_CONFIG "
    "PG_LOGICAL_EMIT_MESSAGE LO_CREAT LO_IMPORT DBLINK PG_READ_FILE PG_LS_DIR PG_STAT_RESET "
    "PG_CURRENT_WAL_LSN PG_RELATION_SIZE PG_TOTAL_RELATION_SIZE PG_TABLE_SIZE PG_INDEXES_SIZE "
    "PG_STAT_STATEMENTS".split()
)
# Aggregates whose result depends on input order unless they have their own ORDER BY.
_ORDER_SENSITIVE_AGGS = frozenset(
    "ARRAY_AGG STRING_AGG JSON_AGG JSONB_AGG JSON_OBJECT_AGG JSONB_OBJECT_AGG XMLAGG JSON_ARRAYAGG "
    "JSON_OBJECTAGG JSON_AGG_STRICT JSONB_AGG_STRICT ANY_VALUE".split()
)
# Window functions that are well-defined among peers (ties).
_TIE_SAFE_WINDOW = frozenset("RANK DENSE_RANK PERCENT_RANK CUME_DIST".split())
_ORDER_DEPENDENT_WINDOW = frozenset("ROW_NUMBER NTILE LAG LEAD FIRST_VALUE LAST_VALUE NTH_VALUE".split())
_AGG_OR_WINDOW = frozenset(
    "SUM AVG STDDEV STDDEV_POP STDDEV_SAMP VARIANCE VAR_POP VAR_SAMP CORR COVAR_POP COVAR_SAMP REGR_SLOPE "
    "REGR_INTERCEPT REGR_R2 REGR_AVGX REGR_AVGY REGR_SXX REGR_SYY REGR_SXY PERCENTILE_CONT OVER".split()
)
# PostgreSQL type OIDs of float4, float8 and their arrays.
FLOAT_OIDS = frozenset({700, 701, 1021, 1022})
NUMERIC_OID = 1700


def eligible(sql: str) -> bool:
    """True if ``sql`` is a read-only query whose result multiset is fully determined
    by the data, so that every correct plan returns the same rows."""
    v = StmtView.of(sql)
    w = v.words
    if v.kind not in ("SELECT", "VALUES", "TABLE"):
        return False
    ws = v.wordset
    if ws & {"INSERT", "UPDATE", "DELETE", "MERGE", "LIMIT", "OFFSET", "FETCH", "TABLESAMPLE", "INTO"}:
        return False
    if v.has("DISTINCT", "ON") or v.has("FOR", "UPDATE") or v.has("FOR", "SHARE") or v.has("SKIP", "LOCKED"):
        return False
    if ws & _VOLATILE:
        return False
    if ws & _ORDER_DEPENDENT_WINDOW and v.has("OVER"):
        return False
    if v.has("OVER") and v.has("ROWS"):
        return False
    for i, x in enumerate(w[:-1]):
        if x in _ORDER_SENSITIVE_AGGS and w[i + 1] == "(" and not _has_order_by_inside(w, i + 1):
            return False
        # ARRAY(SELECT ...) collects rows in scan order, like an unordered array_agg.
        if (x == "ARRAY" and w[i + 1] == "(" and i + 2 < len(w) and w[i + 2] in ("SELECT", "VALUES", "TABLE", "(")
                and not _has_order_by_inside(w, i + 1)):
            return False
    return True


# Stable within a transaction (fine for plan variants on one server) but different
# on two servers: excluded from cross-version comparison.
_TIME_DEPENDENT = frozenset(
    "NOW CURRENT_TIMESTAMP CURRENT_DATE CURRENT_TIME LOCALTIME LOCALTIMESTAMP TRANSACTION_TIMESTAMP "
    "VERSION PG_POSTMASTER_START_TIME PG_CONF_LOAD_TIME INET_SERVER_PORT CURRENT_SETTING PG_BACKEND_PID".split()
)


# Functions whose results changed on purpose between the release and master, so a
# cross-version difference in them is expected. Each entry names the change.
#   corr/regr_*: master keeps Sxx/Syy exactly 0 for constant input (649828769), so
#   corr(x, x) over equal values is NULL on master and 1 on 18.
_XVERSION_CHANGED = frozenset("CORR REGR_R2 REGR_SLOPE REGR_INTERCEPT".split())


def xversion_eligible(sql: str) -> bool:
    """``eligible``, independent of the server instance and the wall clock, and free of
    functions whose behaviour changed on purpose between the two versions."""
    return eligible(sql) and not (StmtView.of(sql).wordset & (_TIME_DEPENDENT | _XVERSION_CHANGED))


def masks_floats(sql: str) -> bool:
    """Aggregates and window frames over floats legitimately differ in the last
    digits between plans (summation order), so float columns are masked."""
    return bool(StmtView.of(sql).wordset & _AGG_OR_WINDOW)


def _has_order_by_inside(words: Sequence[str], open_idx: int) -> bool:
    depth = 0
    for j in range(open_idx, len(words)):
        if words[j] == "(":
            depth += 1
        elif words[j] == ")":
            depth -= 1
            if depth == 0:
                return False
        elif depth == 1 and words[j] == "ORDER" and j + 1 < len(words) and words[j + 1] == "BY":
            return True
    return False


def _canon(v: Any, oid: int | None) -> str:
    """Text of a value with representation choices that no plan controls removed:
    equal numerics with different display scales (2.0 / 2.00) and float -0 / 0
    compare equal, so DISTINCT, GROUP BY and UNION may keep either one."""
    t = str(v)
    if oid == NUMERIC_OID and "." in t and "e" not in t.lower():
        t = t.rstrip("0").rstrip(".")
        return "0" if t in ("-0", "") else t
    if oid in (700, 701) and t in ("-0", "0"):
        return "0"
    return t


def _float_class(v: Any) -> str:
    """A masked float keeps what summation order cannot change: NaN, +-Infinity, finite."""
    t = str(v)
    return t if t in ("NaN", "Infinity", "-Infinity") else "F"


def result_digest(rows: Iterable[Sequence[Any]], type_oids: Sequence[int] | None = None, mask_floats: bool = False,
                  max_rows: int = 10000) -> tuple[str | None, int]:
    """Order-insensitive digest of a result set. Values are expected as text (the
    executor loads every type as text, i.e. PostgreSQL's own output format).
    Returns ``(None, n)`` if there are more than ``max_rows`` rows."""
    masked = {i for i, oid in enumerate(type_oids or []) if oid in FLOAT_OIDS} if mask_floats else set()
    kinds = [oid if oid in (NUMERIC_OID, *FLOAT_OIDS) else None for oid in (type_oids or [])]
    canon = []
    n = 0
    for row in rows:
        n += 1
        if n > max_rows:
            return None, n
        canon.append("\x1f".join("\x00" if v is None else _float_class(v) if i in masked
                                  else _canon(v, kinds[i] if i < len(kinds) else None)
                                  for i, v in enumerate(row)))
    canon.sort()
    h = hashlib.blake2b(digest_size=12)
    for r in canon:
        h.update(r.encode("utf-8", "replace"))
        h.update(b"\x1e")
    return h.hexdigest(), n


def pick_variants(sql: str, names: Sequence[str], k: int) -> list[str]:
    """Deterministic choice of ``k`` variants for one statement (stable across runs,
    so a failure replays with the same variant)."""
    if k >= len(names):
        return list(names)
    seed = zlib.crc32(sql.encode("utf-8", "replace"))
    order = sorted(names, key=lambda n: zlib.crc32(f"{seed}:{n}".encode()))
    return order[:k]


def materialize(statements: list[str], culprit: int, settings: dict[str, str]) -> list[str]:
    """Rewrite a failing test case so the plan variant is explicit: the culprit
    statement runs after ``SET`` commands. Used for replay, minimization and reports."""
    sets = [f"SET {k} = {_quote(v)}" for k, v in settings.items()]
    return statements[:culprit] + sets + statements[culprit:culprit + 1]


def _quote(v: str) -> str:
    return v if v.replace("_", "").replace(".", "").isalnum() and not v[:1].isdigit() or v.isdigit() else f"'{v}'"
