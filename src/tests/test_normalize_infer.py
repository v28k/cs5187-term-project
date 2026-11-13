"""Learned cross-engine normalizers and guards (C4)."""

from pgfuzz.normalizers.infer import Learned, Record, evaluate, infer, query_features


def _rec(sql, a, b):
    return Record(sql, a, b, query_features(sql))


def test_query_features():
    f = query_features("SELECT CAST(a AS REAL), lower(b) || 'x/y', c / 2 FROM t ORDER BY 1")
    assert {"fn:LOWER", "cast:real", "op:||", "op:/", "kw:ORDER BY"} <= f
    assert "op:/" not in query_features("SELECT 'a/b'")            # inside a string literal
    assert "fn:IN" not in query_features("SELECT 1 WHERE x IN (1, 2)")


def _records():
    rs = []
    for i in range(6):     # booleans rendered as true/1
        rs.append(_rec(f"SELECT x > {i} FROM t", [("true",)], [("1",)]))
    for i in range(1, 5):  # floats differing in the last digits
        rs.append(_rec(f"SELECT {i} * 0.1 FROM t", [(repr(i * 0.1 + 1e-15),)], [(repr(i * 0.1),)]))
    for i in range(5):     # integer division: no value normalizer explains it
        rs.append(_rec(f"SELECT c0 / {i + 2} FROM t", [("0.5",)], [("0",)]))
        rs.append(_rec(f"SELECT c0 + {i} FROM t", [("1",)], [("1",)]))
    rs.append(_rec("SELECT broken()", None, [("1",)]))           # an error on one side: not comparable
    return rs


def test_infer_picks_normalizers_then_guards():
    learned = infer(_records())
    assert learned.normalize[:2] == ["bool_int", "float_round_12"]
    assert learned.guards == ["op:/"]
    assert learned.stats["residual_after_guards"] == 0
    assert learned.stats["comparable"] == 20


def test_evaluate_on_held_out_records():
    learned = Learned(["bool_int"], ["op:/"])
    rep = evaluate(learned, _records())
    assert rep["disagree_rate_before"] == round(15 / 20, 4)
    assert rep["disagree_rate_after_normalize"] == round(9 / 20, 4)
    assert rep["guarded_share"] == round(5 / 20, 4)
    assert rep["residual"] == 4                                  # the float records


def test_no_rule_without_support():
    rs = [_rec("SELECT 1", [("true",)], [("1",)])]
    learned = infer(rs, min_support=2)
    assert learned.normalize == [] and learned.guards == []
