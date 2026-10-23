from pgfuzz.core.types import ExecResult, Outcome, StatementResult, StatementStatus as S, TestCase
from pgfuzz.eval import oracle
from pgfuzz.reference.xversion_executor import CrossVersionExecutor


class _Fake:
    def __init__(self, results):
        self.results, self.ran, self.diff_stats = results, [], {}

    def execute(self, tc):
        self.ran.append(tc)
        return ExecResult([StatementResult(**r) for r in self.results])

    def run_outside(self, stmts):
        self.ran.append(("prelude", tuple(stmts)))


def _xv(test_rows, ref_rows, prelude=None):
    x = object.__new__(CrossVersionExecutor)
    x.test, x.ref, x.prelude, x._ref_version = _Fake(test_rows), _Fake(ref_rows), prelude or [], "18.6"
    x.xstats = {"compared": 0, "mismatch": 0, "test_only_ok": 0, "ref_only_ok": 0, "ref_failures": 0}
    return x


def test_different_digests_are_a_wrong_result():
    x = _xv([{"status": S.OK, "rows": 2, "result_hash": "a"}], [{"status": S.OK, "rows": 3, "result_hash": "b"}],
            prelude=["ALTER TABLE t2 ALTER COLUMN c0 RESTART WITH 31"])
    tc = TestCase(["SELECT a1.c0 FROM t0 AS a1"], meta={"checks": [{"stmt": 0}]})
    res = x.execute(tc)
    cls = oracle.classify(res)
    assert cls.outcome is Outcome.WRONG_RESULT and cls.details["variant"] == "xversion"
    assert x.xstats["mismatch"] == 1
    assert "checks" not in x.ref.ran[-1].meta          # the reference runs no metamorphic checks
    assert x.test.ran[0][0] == "prelude" and x.ref.ran[0][0] == "prelude"


def test_clock_dependent_and_one_sided_statements_are_not_compared():
    x = _xv([{"status": S.OK, "result_hash": "a"}, {"status": S.OK, "result_hash": "c"}],
            [{"status": S.OK, "result_hash": "b"}, {"status": S.ERROR, "sqlstate": "42883"}])
    res = x.execute(TestCase(["SELECT now() AS c0", "SELECT new_function(1)"]))
    assert oracle.classify(res).outcome is Outcome.OK
    assert x.xstats == {"compared": 0, "mismatch": 0, "test_only_ok": 1, "ref_only_ok": 0, "ref_failures": 0}
