from pgfuzz.core.types import ExecResult, StatementResult, StatementStatus as S, TestCase
from pgfuzz.eval.oracle import classify
from pgfuzz.eval.signature import compute, normalize_frames, normalize_message


def test_normalize_message():
    a = normalize_message('cache lookup failed for relation 16384 "t0" at 0x7ffd')
    b = normalize_message('cache lookup failed for relation 99 "t17" at 0x1')
    assert a == b == "cache lookup failed for relation N ? at H"


def test_normalize_frames_skips_generic():
    frames = [
        "#0  0x00007f raise (sig=6) at ../sysdeps/raise.c:50",
        "#1  0x00007f in abort () at abort.c:79",
        "#2  0x0000 in ExceptionalCondition (conditionName=...) at assert.c:66",
        "#3  0x0000 in make_outerjoininfo (root=0x1) at initsplan.c:1460",
        "#4  0x0000 in deconstruct_jointree (root=0x1) at initsplan.c:900",
    ]
    assert normalize_frames(frames) == ["make_outerjoininfo", "deconstruct_jointree"]


def _crash(sql):
    tc = TestCase(["SELECT 1", sql])
    res = ExecResult([StatementResult(S.OK), StatementResult(S.CONNECTION_LOST, None, "server closed the connection unexpectedly")])
    return compute(classify(res), tc)


def test_crash_signatures_do_not_collapse_on_client_message():
    a = _crash("SELECT * FROM t0, LATERAL (SELECT 1) s")
    b = _crash("SELECT c0, rank() OVER (ORDER BY c0) FROM t0")
    assert a.strength == b.strength == "weak"
    assert a.id != b.id


def test_same_internal_error_same_signature():
    def sig(msg):
        res = ExecResult([StatementResult(S.ERROR, "XX000", msg)])
        return compute(classify(res), TestCase(["SELECT 1"]))

    assert sig("unrecognized node type: 312").id == sig("unrecognized node type: 7").id
    assert sig("unrecognized node type: 312").id != sig("wrong varno 3 in Var").id


def test_stack_beats_message():
    res = ExecResult([StatementResult(S.CONNECTION_LOST)], backtrace=["#3 0x1 in foo (a=1) at f.c:1"])
    s = compute(classify(res), TestCase(["SELECT 1"]))
    assert s.strength == "stack" and "foo" in s.key
