from pgfuzz.eval.normalize import make


def test_normalizers():
    n = make(["float_text_15", "integral_float", "bool_int"])
    assert n([("0.14285714285714285|1", "2.0", "true", None)]) == [("0.142857142857143|1", "2", "1", None)]
    assert n([("abc", "7", "1e300")]) == [("abc", "7", "1e300")]
    r = make(["float_round_12"])
    assert r([("0.30000000000000004",)]) == [("0.3",)]
    assert make(None) is None
