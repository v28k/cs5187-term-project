"""Harness acceptance checks: does an executor + the oracle report what we expect?

Run this against Member A's harness before any experiment. A fuzzing campaign
on a harness that misreports errors, leaks state between test cases or does not
recover after a lost connection produces meaningless numbers.

Crashes and assertion failures cannot be triggered portably from SQL on a
correct server; those paths are covered by the unit tests with recorded
server-log lines and by replaying known-bug PoCs (``pgfuzz replay``).
"""

from __future__ import annotations

from dataclasses import dataclass

from pgfuzz.core.interfaces import Executor
from pgfuzz.core.types import Outcome, StatementStatus, TestCase
from pgfuzz.eval.oracle import classify


@dataclass
class Check:
    name: str
    statements: list[str]
    expect: list[Outcome | None]  # per statement; None = SKIPPED expected
    why: str


CHECKS = [
    Check("ok", ["SELECT 1"], [Outcome.OK], "plain query succeeds"),
    Check("syntax", ["SELEC 1"], [Outcome.SYNTAX_ERROR], "parser rejections are SQLSTATE 42601"),
    Check("semantic", ["SELECT * FROM pgfuzz_no_such_table"], [Outcome.SEMANTIC_ERROR], "undefined table is 42P01"),
    Check("runtime", ["SELECT 1/0"], [Outcome.RUNTIME_ERROR], "division by zero is 22012"),
    Check("continue", ["SELECT 1/0", "SELECT 1"], [Outcome.RUNTIME_ERROR, Outcome.OK],
          "an error must not abort later statements of the same test case"),
    Check("timeout", ["SELECT pg_sleep(60)"], [Outcome.TIMEOUT], "statement_timeout must be set below 60 s"),
    Check("isolation-a", ["CREATE TABLE pgfuzz_selftest_leak(a int)"], [Outcome.OK], "create a table ..."),
    Check("isolation-b", ["SELECT * FROM pgfuzz_selftest_leak"], [Outcome.SEMANTIC_ERROR],
          "... which must be gone in the next test case (no state leak)"),
    Check("terminate", ["SELECT pg_terminate_backend(pg_backend_pid())", "SELECT 1"],
          [Outcome.CONNECTION_TERMINATED, None],
          "orderly termination is not a crash; later statements are skipped"),
    Check("recover", ["SELECT 1"], [Outcome.OK], "executor reconnects after losing the connection"),
]


@dataclass
class CheckResult:
    check: Check
    passed: bool
    got: list[str]
    error: str | None = None


def run_selftest(executor: Executor) -> list[CheckResult]:
    out = []
    executor.start()
    try:
        for i, c in enumerate(CHECKS):
            try:
                res = executor.execute(TestCase(list(c.statements), origin="selftest", id=i))
                cls = classify(res)
                got: list[Outcome | None] = [
                    None if st.status is StatementStatus.SKIPPED else oc
                    for st, oc in zip(res.statements, cls.statement_outcomes)
                ]
                labels = [g.value if g else "skipped" for g in got]
                detail = "; ".join(f"{st.sqlstate or '-'} {st.message or ''}".strip() for st in res.statements if st.status is not StatementStatus.OK)
                out.append(CheckResult(c, got == c.expect, labels, detail or None))
            except Exception as e:
                out.append(CheckResult(c, False, [], f"{type(e).__name__}: {e}"))
    finally:
        executor.stop()
    return out
