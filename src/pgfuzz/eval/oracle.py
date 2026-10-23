"""Failure oracle: turns raw executor facts into an :class:`Outcome`.

Rules, in priority order for a test case:

1. Server-log evidence: ``TRAP:`` (assertion), sanitizer reports, ``terminated by signal``, ``PANIC:``.
2. Connection loss without an orderly termination SQLSTATE: crash.
3. SQLSTATE of each failing statement, mapped by class (PostgreSQL Appendix A).
4. Differential facts of successful statements: a plan variant that raised an
   internal error, or returned a different result multiset (``wrong_result``).
5. Metamorphic facts of successful statements: a confirmed mismatch between
   the two sides of a check (``wrong_result``, variant ``mm:<kind>``), or an
   internal error raised by a follow-up query. Unconfirmed mismatches (the
   re-run disagreed with the first run) are non-deterministic and ignored.

When the culprit is a bug candidate, the C backtrace that PostgreSQL printed to
the server log (after an assertion, or for internal errors with
``backtrace_on_internal_error``) is attached for stack-based deduplication.

The test-case outcome is the most severe statement outcome. The SQLSTATE mapping
is the single place where "is this a bug candidate?" is decided.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pgfuzz.core.types import ExecResult, Outcome, StatementResult, StatementStatus

# Parser rejections. 42601 covers both grammar and lexer errors.
_SYNTAX = {"42601"}

# Orderly terminations that are not bugs (e.g. pg_terminate_backend on itself).
_TERMINATED = {"57P01", "57P04", "57P05"}
# Another backend crashed and the postmaster is resetting shared memory.
_CRASH_SHUTDOWN = {"57P02"}

_SQLSTATE_CLASS = {
    "42": Outcome.SEMANTIC_ERROR,  # syntax error or access rule violation (non-42601)
    "0A": Outcome.SEMANTIC_ERROR,  # feature not supported
    "25": Outcome.SEMANTIC_ERROR,  # invalid transaction state
    "26": Outcome.SEMANTIC_ERROR,  # invalid SQL statement name
    "28": Outcome.SEMANTIC_ERROR,  # invalid authorization
    "2B": Outcome.SEMANTIC_ERROR,
    "2D": Outcome.SEMANTIC_ERROR,
    "34": Outcome.SEMANTIC_ERROR,  # invalid cursor name
    "3D": Outcome.SEMANTIC_ERROR,  # invalid catalog name
    "3F": Outcome.SEMANTIC_ERROR,  # invalid schema name
    "0L": Outcome.SEMANTIC_ERROR,
    "0P": Outcome.SEMANTIC_ERROR,
    "53": Outcome.RESOURCE_LIMIT,  # insufficient resources
    "54": Outcome.RESOURCE_LIMIT,  # program limit exceeded
    "XX": Outcome.INTERNAL_ERROR,
}

_SQLSTATE_EXACT = {
    "57014": Outcome.TIMEOUT,  # query_canceled (statement_timeout)
    "XX001": Outcome.DATA_CORRUPTION,
    "XX002": Outcome.DATA_CORRUPTION,
}

# Internal errors (XX000) that are almost always resource exhaustion rather than
# logic bugs. Kept small and explicit so it can be reported in the paper.
DEFAULT_BENIGN_INTERNAL = (
    re.compile(r"invalid memory alloc request size", re.I),
)

# elog(ERROR) messages that indicate an internal invariant violation. Used only
# when the executor could not supply a SQLSTATE.
_INTERNAL_MESSAGE = re.compile(
    r"cache lookup failed|unrecognized node type|unexpected |could not find |"
    r"variable not found in subplan|wrong varno|plan should not reference|"
    r"no relation entry for relid|could not devise a query plan|"
    r"negative bitmapset member|bogus |unrecognized .* kind",
    re.I,
)

_TRAP_NEW = re.compile(r'TRAP: failed Assert\("(?P<expr>.*)"\), File: "(?P<file>[^"]+)", Line: (?P<line>\d+)')
_TRAP_OLD = re.compile(r'TRAP: (?:FailedAssertion|BadArgument|BadState)\("(?P<expr>.*)", File: "(?P<file>[^"]+)", Line: (?P<line>\d+)')
_SIGNAL = re.compile(r"was terminated by (?:signal (?P<sig>\d+)(?:: (?P<name>[^\n]+))?|exception (?P<exc>0x[0-9A-Fa-f]+))")
_PANIC = re.compile(r"\bPANIC:\s+(?P<msg>.*)")
# AddressSanitizer / UndefinedBehaviorSanitizer reports (sanitizer builds only).
_ASAN = re.compile(r"ERROR: (?P<tool>AddressSanitizer|LeakSanitizer|MemorySanitizer|ThreadSanitizer): (?P<kind>[\w-]+)")
_UBSAN = re.compile(r"(?P<file>[\w./-]+\.[ch]):(?P<line>\d+):\d+: runtime error: (?P<msg>.*)")

# Backtrace frames printed by PostgreSQL itself: after an assertion failure
# (ExceptionalCondition, PG 13+) and for internal errors with
# backtrace_on_internal_error = on (PG 17+). glibc format: "binary(function+0x1f) [0xaddr]".
_GLIBC_FRAME = re.compile(r"\((?P<fn>[A-Za-z_][A-Za-z0-9_]*)\+0x[0-9a-fA-F]+\)\s*\[0x[0-9a-fA-F]+\]")
_GLIBC_ANON_FRAME = re.compile(r"\(\+0x[0-9a-fA-F]+\)\s*\[0x[0-9a-fA-F]+\]")
# Sanitizer / gdb frames: "#3 0x55d1 in ExecInitAgg /src/nodeAgg.c:123".
_SAN_FRAME = re.compile(r"^\s*#\d+\s+0x[0-9a-fA-F]+\s+in\s+(?P<fn>[A-Za-z_][A-Za-z0-9_:.]*)")
_BT_START = re.compile(r"TRAP:|BACKTRACE:|ERROR: \w+Sanitizer|runtime error:")


def backtrace_from_log(lines: list[str]) -> list[str]:
    """Function names of the first backtrace block in server-log lines.

    The block that follows an assertion (``TRAP:``) wins over one that follows an
    internal error (``BACKTRACE:``), because the assertion is what crashed."""
    blocks: list[tuple[int, list[str]]] = []
    cur: list[str] | None = None
    prio = 0
    for line in lines:
        if _BT_START.search(line):
            if cur:
                blocks.append((prio, cur))
            cur = []
            prio = 2 if ("TRAP:" in line or "Sanitizer" in line or "runtime error" in line) else 1
            continue
        if cur is None:
            continue
        m = _GLIBC_FRAME.search(line) or _SAN_FRAME.search(line)
        if m:
            cur.append(m["fn"])
        elif _GLIBC_ANON_FRAME.search(line):
            continue  # static function without a symbol name
        elif cur and line.strip() and not line.startswith((" ", "\t")):
            blocks.append((prio, cur))
            cur = None
    if cur:
        blocks.append((prio, cur))
    if not blocks:
        return []
    best = max(blocks, key=lambda b: b[0])
    return best[1]


@dataclass
class Classification:
    outcome: Outcome
    statement_outcomes: list[Outcome]
    culprit: int | None = None
    sqlstate: str | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def is_bug_candidate(self) -> bool:
        return self.outcome.is_bug_candidate


def classify_sqlstate(
    sqlstate: str | None,
    message: str | None = None,
    benign_internal: tuple[re.Pattern[str], ...] = DEFAULT_BENIGN_INTERNAL,
) -> Outcome:
    msg = message or ""
    if sqlstate is None:
        return Outcome.INTERNAL_ERROR if _INTERNAL_MESSAGE.search(msg) else Outcome.RUNTIME_ERROR
    sqlstate = sqlstate.upper()
    if sqlstate in _SYNTAX:
        return Outcome.SYNTAX_ERROR
    if sqlstate in _TERMINATED:
        return Outcome.CONNECTION_TERMINATED
    if sqlstate in _CRASH_SHUTDOWN:
        return Outcome.CRASH
    if sqlstate in _SQLSTATE_EXACT:
        return _SQLSTATE_EXACT[sqlstate]
    outcome = _SQLSTATE_CLASS.get(sqlstate[:2], Outcome.RUNTIME_ERROR)
    if outcome is Outcome.INTERNAL_ERROR and any(p.search(msg) for p in benign_internal):
        return Outcome.RESOURCE_LIMIT
    return outcome


def scan_server_log(lines: list[str]) -> dict[str, Any]:
    """Extract crash evidence from server-log lines written during one test case."""
    found: dict[str, Any] = {}
    for line in lines:
        m = _TRAP_NEW.search(line) or _TRAP_OLD.search(line)
        if m and "assertion" not in found:
            found["assertion"] = {"expr": m["expr"], "file": m["file"], "line": int(m["line"])}
            continue
        m = _SIGNAL.search(line)
        if m and "signal" not in found:
            found["signal"] = int(m["sig"]) if m["sig"] else m["exc"]
            if m["name"]:
                found["signal_name"] = m["name"].strip()
            continue
        m = _PANIC.search(line)
        if m and "panic" not in found:
            found["panic"] = m["msg"].strip()
            continue
        m = _ASAN.search(line)
        if m and "sanitizer" not in found:
            found["sanitizer"] = {"tool": m["tool"], "kind": m["kind"]}
            continue
        m = _UBSAN.search(line)
        if m and "sanitizer" not in found:
            found["sanitizer"] = {"tool": "UndefinedBehaviorSanitizer", "kind": m["msg"].strip()[:120],
                                  "file": m["file"].rsplit("/", 1)[-1], "line": int(m["line"])}
    return found


def classify_variants(st: StatementResult, benign_internal: tuple[re.Pattern[str], ...]) -> tuple[Outcome, dict[str, Any]] | None:
    """Judge plan-variant facts of one successful statement (differential oracle)."""
    if not st.variants:
        return None
    for name, v in st.variants.items():
        status = v.get("status")
        if status == "error":
            oc = classify_sqlstate(v.get("sqlstate"), v.get("message"), benign_internal)
            if oc.is_bug_candidate:
                return oc, {"variant": name, "settings": v.get("settings", {}), "sqlstate": v.get("sqlstate"),
                            "message": v.get("message")}
        elif status == "ok" and st.result_hash and v.get("hash") and v["hash"] != st.result_hash:
            return Outcome.WRONG_RESULT, {
                "variant": name, "settings": v.get("settings", {}), "sqlstate": None,
                "message": f"result differs under plan variant {name}: {st.rows} rows by default, {v.get('rows')} rows with variant",
                "rows_default": st.rows, "rows_variant": v.get("rows"),
            }
    return None


def classify_checks(st: StatementResult, benign_internal: tuple[re.Pattern[str], ...]) -> tuple[Outcome, dict[str, Any]] | None:
    """Judge metamorphic-check facts of one successful statement."""
    for c in st.checks or ():
        kind = c.get("kind", "?")
        if c.get("status") == "error":
            oc = classify_sqlstate(c.get("sqlstate"), c.get("message"), benign_internal)
            if oc.is_bug_candidate:
                return oc, {"oracle": "metamorphic", "variant": f"mm:{kind}", "check": kind, "side": c.get("side"),
                            "check_sql": c.get("sql"), "sqlstate": c.get("sqlstate"), "message": c.get("message")}
        elif c.get("status") == "ok" and c.get("cert_violation"):
            return Outcome.PERFORMANCE, {
                "oracle": "cert", "variant": "mm:cert", "check": kind, "sqlstate": None,
                "message": f"row estimate rises when the WHERE clause is added: "
                           f"{c.get('lhs_estimate')} -> {c.get('rhs_estimate')}",
                "lhs_sql": c.get("lhs_sql"), "rhs_sql": c.get("rhs_sql"),
                "estimate_lhs": c.get("lhs_estimate"), "estimate_rhs": c.get("rhs_estimate"),
            }
        elif c.get("status") == "ok" and c.get("confirmed") and c.get("lhs_hash") != c.get("rhs_hash"):
            return Outcome.WRONG_RESULT, {
                "oracle": "metamorphic", "variant": f"mm:{kind}", "check": kind, "sqlstate": None,
                "message": f"metamorphic check {kind} failed: {c.get('lhs_rows')} rows vs {c.get('rhs_rows')} rows",
                "lhs_sql": c.get("lhs_sql"), "rhs_sql": c.get("rhs_sql"),
                "rows_lhs": c.get("lhs_rows"), "rows_rhs": c.get("rhs_rows"),
            }
    return None


def classify(
    result: ExecResult,
    benign_internal: tuple[re.Pattern[str], ...] = DEFAULT_BENIGN_INTERNAL,
) -> Classification:
    outcomes: list[Outcome] = []
    lost_at: int | None = None
    variant_info: dict[int, dict[str, Any]] = {}
    for i, st in enumerate(result.statements):
        if st.status is StatementStatus.OK:
            vo = classify_variants(st, benign_internal) or classify_checks(st, benign_internal)
            if vo is None:
                outcomes.append(Outcome.OK)
            else:
                outcomes.append(vo[0])
                variant_info[i] = vo[1]
        elif st.status is StatementStatus.SKIPPED:
            outcomes.append(Outcome.OK)
        elif st.status is StatementStatus.CONNECTION_LOST:
            if result.extra.get("foreign_crash") or (
                    st.sqlstate and classify_sqlstate(st.sqlstate) is Outcome.CONNECTION_TERMINATED):
                outcomes.append(Outcome.CONNECTION_TERMINATED)
            else:
                outcomes.append(Outcome.CRASH)
            lost_at = i if lost_at is None else lost_at
        else:
            outcomes.append(classify_sqlstate(st.sqlstate, st.message, benign_internal))

    evidence = scan_server_log(result.server_log)
    details: dict[str, Any] = dict(evidence)

    log_outcome: Outcome | None = None
    if "assertion" in evidence:
        log_outcome = Outcome.ASSERTION
    elif "sanitizer" in evidence:
        log_outcome = Outcome.SANITIZER
    elif "signal" in evidence:
        log_outcome = Outcome.CRASH
    elif "panic" in evidence:
        log_outcome = Outcome.PANIC

    if log_outcome is not None:
        idx = lost_at if lost_at is not None else _last_executed(result)
        if idx is not None and outcomes:
            # The log says *why* the connection dropped, so it refines a generic crash.
            if outcomes[idx].severity < log_outcome.severity or outcomes[idx] is Outcome.CRASH:
                outcomes[idx] = log_outcome
        elif not outcomes:
            outcomes.append(log_outcome)

    if not outcomes:
        return Classification(Outcome.OK, [], details=details)

    culprit = max(range(len(outcomes)), key=lambda i: (outcomes[i].severity, -i))
    worst = outcomes[culprit]
    if worst is Outcome.OK:
        return Classification(Outcome.OK, outcomes, details=details)

    st = result.statements[culprit] if culprit < len(result.statements) else None
    sqlstate = st.sqlstate if st else None
    message = st.message if st else None
    if st is not None and st.status is StatementStatus.CONNECTION_LOST:
        details["connection_lost"] = True
        lost_variant = next((n for n, v in (st.variants or {}).items() if v.get("status") == "connection_lost"), None)
        if lost_variant:
            details["variant"] = lost_variant
            details["settings"] = st.variants[lost_variant].get("settings", {})
        lost_check = next((c for c in (st.checks or []) if c.get("status") == "connection_lost"), None)
        if lost_check and not lost_variant:
            details.update(oracle="metamorphic", variant=f"mm:{lost_check.get('kind')}",
                           check=lost_check.get("kind"), check_sql=lost_check.get("sql"))
    if culprit in variant_info:
        info = variant_info[culprit]
        details.update({k: v for k, v in info.items() if k not in ("sqlstate", "message")})
        sqlstate, message = info.get("sqlstate"), info.get("message")
    if result.backtrace:
        details["backtrace"] = list(result.backtrace)
    elif worst.is_bug_candidate and worst is not Outcome.WRONG_RESULT:
        frames = backtrace_from_log(result.server_log)
        if frames:
            details["backtrace"] = frames
    return Classification(
        outcome=worst,
        statement_outcomes=outcomes,
        culprit=culprit,
        sqlstate=sqlstate,
        message=message,
        details=details,
    )


def _last_executed(result: ExecResult) -> int | None:
    last = None
    for i, st in enumerate(result.statements):
        if st.status is not StatementStatus.SKIPPED:
            last = i
    return last
