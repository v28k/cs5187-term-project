"""Data types shared by generators (Member B), executors (Member A) and evaluation (Member C).

The contract is intentionally small:

* a generator produces a :class:`TestCase` (an ordered list of SQL statements);
* an executor runs it and returns a raw :class:`ExecResult` (what the server said);
* evaluation turns the raw result into an :class:`Outcome` and metrics.

Executors never decide whether something is a bug. They report facts (SQLSTATE,
message, connection loss, server-log lines); the oracle in ``pgfuzz.eval.oracle``
classifies them, so every configuration is judged by exactly the same rules.
"""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from typing import Any


class StatementStatus(str, enum.Enum):
    OK = "ok"
    ERROR = "error"
    CONNECTION_LOST = "connection_lost"
    SKIPPED = "skipped"


class Outcome(str, enum.Enum):
    """Classified result of one statement or one test case, ordered by severity."""

    OK = "ok"
    SYNTAX_ERROR = "syntax_error"
    SEMANTIC_ERROR = "semantic_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    CONNECTION_TERMINATED = "connection_terminated"
    PERFORMANCE = "performance"      # a cardinality-estimation inconsistency (CERT); not a wrong answer
    WRONG_RESULT = "wrong_result"
    INTERNAL_ERROR = "internal_error"
    DATA_CORRUPTION = "data_corruption"
    PANIC = "panic"
    ASSERTION = "assertion"
    SANITIZER = "sanitizer"
    CRASH = "crash"

    @property
    def severity(self) -> int:
        return _SEVERITY[self]

    @property
    def is_bug_candidate(self) -> bool:
        return self in BUG_CANDIDATES

    @property
    def parsed(self) -> bool:
        """True if the statement got past the PostgreSQL parser."""
        return self is not Outcome.SYNTAX_ERROR


_SEVERITY = {o: i for i, o in enumerate(Outcome)}

BUG_CANDIDATES = frozenset(
    {
        Outcome.PERFORMANCE,
        Outcome.WRONG_RESULT,
        Outcome.INTERNAL_ERROR,
        Outcome.DATA_CORRUPTION,
        Outcome.PANIC,
        Outcome.ASSERTION,
        Outcome.SANITIZER,
        Outcome.CRASH,
    }
)


@dataclass
class TestCase:
    """An ordered SQL script. ``meta`` is free-form provenance from the generator
    (grammar rules used, parent test case, mutation operator, LLM prompt id, ...)."""

    statements: list[str]
    origin: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    id: int = -1

    __test__ = False  # stop pytest from collecting this class

    def to_sql(self) -> str:
        return "\n".join(s.rstrip().rstrip(";") + ";" for s in self.statements) + "\n"


@dataclass
class StatementResult:
    """``result_hash`` is a digest of the result multiset, and ``variants`` maps a
    plan-variant name (e.g. ``"no_hashjoin"``) to what the same statement returned
    under that planner setting: ``{"status", "sqlstate", "message", "hash", "rows", "settings"}``.
    Both are filled only when the executor runs the differential oracle.

    ``checks`` holds the outcome of metamorphic checks the generator attached to
    the statement (``TestCase.meta["checks"]``, see ``pgfuzz.grammar.rewrite``):
    ``{"kind", "status", "lhs_hash", "rhs_hash", "lhs_rows", "rhs_rows", "confirmed", ...}``.
    ``plan_shape`` is a digest of the plan's node types (plan-shape guidance)."""

    status: StatementStatus
    sqlstate: str | None = None
    message: str | None = None
    duration_ms: float = 0.0
    rows: int | None = None
    result_hash: str | None = None
    variants: dict[str, dict[str, Any]] | None = None
    checks: list[dict[str, Any]] | None = None
    plan_shape: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        for k in ("result_hash", "variants", "checks", "plan_shape"):
            if d[k] is None:
                d.pop(k)
        return d


@dataclass
class ExecResult:
    """Raw facts about executing one test case.

    ``statements`` is aligned with ``TestCase.statements``. Statements after a
    connection loss are reported as ``SKIPPED``. ``server_log`` holds server-log
    lines emitted while the test case ran (used to detect TRAP / PANIC / signals).
    ``backtrace`` holds symbolized frames if the harness captured a core dump.
    """

    statements: list[StatementResult]
    wall_ms: float = 0.0
    server_log: list[str] = field(default_factory=list)
    backtrace: list[str] | None = None
    server_restarted: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageSample:
    """A point-in-time code-coverage measurement from the instrumented server.

    Any subset of fields may be filled in; ``edges`` is meant for
    SanitizerCoverage / AFL-style edge counters, the line/branch fields for gcov/llvm-cov.
    """

    lines_covered: int | None = None
    lines_total: int | None = None
    branches_covered: int | None = None
    branches_total: int | None = None
    functions_covered: int | None = None
    edges: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
