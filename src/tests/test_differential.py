import pytest

from pgfuzz.eval.differential import eligible


@pytest.mark.parametrize(
    "sql,expected",
    [
        ("SELECT a1.c0 FROM t0 AS a1 WHERE a1.c0 > 0", True),
        ("SELECT a1.c0 FROM t0 AS a1 LIMIT 1", False),
        ("SELECT string_agg(a1.c1, ',') FROM t0 AS a1", False),
        ("SELECT string_agg(a1.c1, ',' ORDER BY a1.c1) FROM t0 AS a1", True),
        # ARRAY(subquery) without ORDER BY depends on the scan order (seen in the cloud hunt:
        # EXCEPT ALL under enable_hashagg on/off returned the same elements in another order).
        ("SELECT ARRAY (SELECT a4.c1 FROM t4 AS a4 EXCEPT ALL SELECT 16) AS c0 FROM t2 AS a1", False),
        ("SELECT ARRAY (SELECT a4.c1 FROM t4 AS a4 ORDER BY 1) AS c0 FROM t2 AS a1", True),
        ("SELECT ARRAY[1, 2] AS c0 FROM t2 AS a1", True),
    ],
)
def test_eligible(sql, expected):
    assert eligible(sql) is expected


def test_digest_ignores_representation_choices():
    from pgfuzz.eval.differential import result_digest

    num, f8, txt = 1700, 701, 25
    # DISTINCT may keep 21.0000 or 21.00 (equal numerics), -0 or 0 (equal floats)
    assert result_digest([["21.0000", "-0"]], [num, f8])[0] == result_digest([["21.00", "0"]], [num, f8])[0]
    assert result_digest([["0.00"]], [num])[0] == result_digest([["0"]], [num])[0]
    assert result_digest([["21.5"]], [num])[0] != result_digest([["21.05"]], [num])[0]
    assert result_digest([["2.0"]], [txt])[0] != result_digest([["2.00"]], [txt])[0]   # text stays exact
    # masked float aggregates still distinguish NaN / Infinity from finite values
    assert result_digest([["NaN"]], [f8], True)[0] != result_digest([["0"]], [f8], True)[0]
    assert result_digest([["0.30000000000000004"]], [f8], True)[0] == result_digest([["0.3"]], [f8], True)[0]


def test_crash_of_another_backend_is_not_ours():
    from pgfuzz.core.types import ExecResult, StatementResult, StatementStatus as S
    from pgfuzz.eval import oracle
    from pgfuzz.reference.pg_executor import _foreign_crash

    trap = 'TRAP: failed Assert("x"), File: "a.c", Line: 1, PID: 1115'
    gone = "2026-10-23 19:21:32.758 UTC [9316] LOG:  client backend (PID 1115) was terminated by signal 6: Aborted"
    assert _foreign_crash([trap, gone], own_pid=2000) == [1115]
    assert _foreign_crash([trap, gone], own_pid=1115) == []          # our own crash
    assert _foreign_crash(["[9316] LOG:  background worker \"parallel worker\" (PID 77) was terminated by signal 11"],
                          own_pid=2000) == []                          # our query's worker
    assert _foreign_crash([trap], own_pid=None) == []
    res = ExecResult([StatementResult(S.CONNECTION_LOST, "57P02", "terminating connection because of crash")],
                     extra={"foreign_crash": [1115]})
    assert not oracle.classify(res).is_bug_candidate
