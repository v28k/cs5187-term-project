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


def test_mine_suite_finds_a_rule_the_grammar_never_fired(tmp_path):
    f = tmp_path / "t.sql"
    f.write_text("-- imported from test\nCREATE TABLE s(a INT);\nINSERT INTO s VALUES (1), (2);\n"
                 "SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1;\n")
    mined = {"kernels": {}, "fires": {}, "rules": K.Lab(CFG).rules}
    out = K.mine_suite(CFG, [f], mined, per_rule=1, budget=60, mem_limit_gb=None, log=lambda _m: None)
    assert out["suite_stats"]["probed"] == 1
    assert "BalancedMerge" in out["kernels"]
    k = out["kernels"]["BalancedMerge"][0]
    assert k["source"] == "suite" and k["tokens"] <= k["tokens_before"]
    assert "BalancedMerge" in K.Lab(CFG).fired(k["setup"], k["query"], ["BalancedMerge"])


def test_transfer_maps_source_rules_to_target_rules():
    mined = {"engine": "other", "kernels": {
        "src_rule": [{"setup": [], "query": "SELECT 5 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 10 ORDER BY 1"}],
        "bad": [{"setup": [], "query": "SELEC nonsense"}]}}
    tr = K.transfer(mined, CFG, mem_limit_gb=None)
    assert tr["kernels"] == 2 and tr["ran"] == 1 and sum(tr["errors"].values()) == 1
    assert "BalancedMerge" in tr["mapping"]["src_rule"] and "BalancedMerge" in tr["target_rules_reached"]


def test_duckdb_rule_probe_adds_to_a_test_cases_own_disabled_optimizers():
    pytest.importorskip("duckdb")
    lab = K.Lab("configs/duckdb.yaml")
    q = "SELECT ' '::text AS c0 FROM t3 AS a1 GROUP BY a1.c2"
    fired = lab.fired(["SET disabled_optimizers = 'join_order'"], q)
    assert fired is not None and len(fired) < 10          # not "every rule fires"
    assert "join_order" not in fired                       # already off in the test case


def test_sqlite_rule_probe_keeps_a_test_cases_own_pragmas():
    lab = K.Lab(CFG)
    q = "SELECT a.c0 FROM t0 AS a JOIN t1 AS b ON a.c1 = b.c1"      # uses an automatic index
    plain = lab.fired([], q)
    for setup in (["PRAGMA automatic_index = 0"], ["PRAGMA reverse_unordered_selects = 1"]):
        got = lab.fired(setup, q)
        # before the fix, resetting the PRAGMA after the first probe made 29 of 30 rules "fire"
        assert got is not None and len(got) <= len(plain) + 2, (setup, got)
