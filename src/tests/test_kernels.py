"""Rule kernels: mining (reduction under "the rule still fires") and composition seeds."""

import pytest

pytest.importorskip("apsw")

from pgfuzz.grammar.generator import parse_seed  # noqa: E402
from pgfuzz.rules import kernels as K  # noqa: E402

CFG = "configs/sqlite.yaml"


def test_templates_are_consistent_on_plain_queries():
    lab = K.Lab(CFG)
    a, b = "SELECT 1 AS x UNION ALL SELECT 2", "SELECT 3 AS y WHERE 1 = 0"
    for name, (comp, want) in K.TEMPLATES.items():
        got, exp = lab.rows([], comp.format(A=a, B=b)), lab.rows([], want.format(A=a, B=b))
        assert got is not None and got == exp, name
        got, exp = lab.rows([], comp.format(A=b, B=a)), lab.rows([], want.format(A=b, B=a))
        assert got is not None and got == exp, name


def test_mine_and_compose(tmp_path):
    mined = K.mine(CFG, n=40, seed=3, per_rule=1, budget=25, log=lambda _m: None)
    assert mined["engine"] == "sqlite" and mined["kernels"]
    lab = K.Lab(CFG)
    for rule, ks in mined["kernels"].items():
        for k in ks:
            assert rule in lab.fired(k["setup"], k["query"], [rule])      # a kernel fires its rule
            assert k["tokens"] <= k["tokens_before"] or k["tokens_before"] == 0
    st = K.compose(CFG, mined, tmp_path / "seeds", per_pair=1, log=lambda _m: None)
    assert not st["violations"]
    pairs = list((tmp_path / "seeds").glob("pair_*.sql"))
    if len(mined["kernels"]) > 1:
        assert pairs and st["seeds"] == len(pairs)
        stmts, checks = parse_seed(pairs[0].read_text())
        assert checks and checks[0]["kind"].startswith("kernel:")


def test_graft_keeps_the_result():
    import random

    lab = K.Lab(CFG)
    a = "SELECT a1.c0 AS c0 FROM t0 AS a1 WHERE a1.c0 IS NOT NULL"
    for kind in K.GRAFTS:
        g = K.graft(a, "SELECT 1 AS z", kind, random.Random(1))
        assert g is not None and "kb" in g and lab.rows([], g) == lab.rows([], a), kind
    assert K.graft("SELECT 1", "SELECT 2", "graft_scalar", random.Random(1)) is None
