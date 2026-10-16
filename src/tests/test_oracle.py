import pytest

from pgfuzz.core.types import ExecResult, Outcome, StatementResult, StatementStatus as S
from pgfuzz.eval.oracle import classify, classify_sqlstate, scan_server_log


@pytest.mark.parametrize(
    "sqlstate,msg,expected",
    [
        ("42601", "syntax error at or near \"x\"", Outcome.SYNTAX_ERROR),
        ("42P01", "relation \"t9\" does not exist", Outcome.SEMANTIC_ERROR),
        ("42883", "function foo() does not exist", Outcome.SEMANTIC_ERROR),
        ("0A000", "not supported", Outcome.SEMANTIC_ERROR),
        ("25001", "VACUUM cannot run inside a transaction block", Outcome.SEMANTIC_ERROR),
        ("22012", "division by zero", Outcome.RUNTIME_ERROR),
        ("23505", "duplicate key", Outcome.RUNTIME_ERROR),
        ("40P01", "deadlock detected", Outcome.RUNTIME_ERROR),
        ("57014", "canceling statement due to statement timeout", Outcome.TIMEOUT),
        ("53200", "out of memory", Outcome.RESOURCE_LIMIT),
        ("54001", "stack depth limit exceeded", Outcome.RESOURCE_LIMIT),
        ("57P01", "terminating connection due to administrator command", Outcome.CONNECTION_TERMINATED),
        ("57P02", "terminating connection because of crash of another server process", Outcome.CRASH),
        ("XX000", "unrecognized node type: 312", Outcome.INTERNAL_ERROR),
        ("XX000", "invalid memory alloc request size 2147483648", Outcome.RESOURCE_LIMIT),
        ("XX001", "invalid page in block 0", Outcome.DATA_CORRUPTION),
        ("xx000", "cache lookup failed for type 0", Outcome.INTERNAL_ERROR),
        (None, "cache lookup failed for relation 123", Outcome.INTERNAL_ERROR),
        (None, "something odd", Outcome.RUNTIME_ERROR),
    ],
)
def test_sqlstate_mapping(sqlstate, msg, expected):
    assert classify_sqlstate(sqlstate, msg) is expected


def test_bug_candidates():
    assert Outcome.CRASH.is_bug_candidate and Outcome.ASSERTION.is_bug_candidate
    assert Outcome.INTERNAL_ERROR.is_bug_candidate
    assert not Outcome.TIMEOUT.is_bug_candidate and not Outcome.CONNECTION_TERMINATED.is_bug_candidate


def test_trap_formats():
    new = 'TRAP: failed Assert("var->varno < root->simple_rel_array_size"), File: "relnode.c", Line: 412, PID: 77'
    old = 'TRAP: FailedAssertion("!(IsA(node, Var))", File: "setrefs.c", Line: 2201, PID: 12)'
    assert scan_server_log([new])["assertion"] == {"expr": "var->varno < root->simple_rel_array_size", "file": "relnode.c", "line": 412}
    assert scan_server_log([old])["assertion"]["file"] == "setrefs.c"


def test_signal_and_panic():
    ev = scan_server_log([
        "2026-10-07 LOG:  server process (PID 9) was terminated by signal 11: Segmentation fault",
        "2026-10-07 PANIC:  could not locate a valid checkpoint record",
    ])
    assert ev["signal"] == 11 and ev["signal_name"] == "Segmentation fault"
    assert ev["panic"] == "could not locate a valid checkpoint record"


def _res(*sts, log=()):
    return ExecResult(list(sts), server_log=list(log))


def test_all_ok():
    c = classify(_res(StatementResult(S.OK), StatementResult(S.OK)))
    assert c.outcome is Outcome.OK and c.culprit is None


def test_worst_statement_wins_and_culprit():
    c = classify(_res(StatementResult(S.ERROR, "42601", "x"), StatementResult(S.ERROR, "XX000", "wrong varno"), StatementResult(S.OK)))
    assert c.outcome is Outcome.INTERNAL_ERROR
    assert c.culprit == 1 and c.sqlstate == "XX000"
    assert c.statement_outcomes == [Outcome.SYNTAX_ERROR, Outcome.INTERNAL_ERROR, Outcome.OK]


def test_connection_loss_is_crash():
    c = classify(_res(StatementResult(S.OK), StatementResult(S.CONNECTION_LOST, None, "server closed the connection unexpectedly"), StatementResult(S.SKIPPED)))
    assert c.outcome is Outcome.CRASH and c.culprit == 1 and c.details["connection_lost"]


def test_orderly_termination_is_not_crash():
    c = classify(_res(StatementResult(S.CONNECTION_LOST, "57P01", "terminating connection"), StatementResult(S.SKIPPED)))
    assert c.outcome is Outcome.CONNECTION_TERMINATED and not c.is_bug_candidate


def test_assertion_from_log_upgrades_crash():
    trap = 'TRAP: failed Assert("x"), File: "a.c", Line: 1, PID: 2'
    c = classify(_res(StatementResult(S.CONNECTION_LOST), log=[trap, "LOG:  server process (PID 2) was terminated by signal 6: Aborted"]))
    assert c.outcome is Outcome.ASSERTION
    assert c.details["assertion"]["file"] == "a.c" and c.details["signal"] == 6


def test_log_evidence_without_connection_loss():
    # e.g. another backend crashed; attribute to the last executed statement
    c = classify(_res(StatementResult(S.OK), StatementResult(S.OK), log=["LOG:  server process (PID 3) was terminated by signal 11"]))
    assert c.outcome is Outcome.CRASH and c.culprit == 1
