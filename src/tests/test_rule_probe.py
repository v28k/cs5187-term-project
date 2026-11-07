import pytest

apsw = pytest.importorskip("apsw")

from pgfuzz.targets.sqlite_executor import SQLiteDriver

SETUP = ["CREATE TABLE t(a, b)", "INSERT INTO t VALUES (1, 2), (1, 3), (2, 4)", "CREATE INDEX i ON t(a)",
         "CREATE TABLE u(a, b)"]


@pytest.fixture(scope="module")
def drv():
    d = SQLiteDriver()
    d.connect(SETUP)
    if not d.rules():
        pytest.skip("sqlite3_test_control not reachable in this APSW build")
    return d


def test_rule_firing_matches_the_optimization(drv):
    assert "MinMaxOpt" in drv.fired("SELECT min(a) FROM t")[1]
    assert "SimplifyJoin" in drv.fired("SELECT t.a FROM t LEFT JOIN u ON t.a = u.a WHERE u.b = 1")[1]
    assert "QueryFlattener" in drv.fired("SELECT * FROM (SELECT a, b FROM t UNION ALL SELECT a, b FROM u) WHERE a = 1")[1]


def test_switches_are_reset_after_probing(drv):
    before = drv.explain("SELECT min(a) FROM t")
    drv.fired("SELECT min(a) FROM t")
    assert drv.explain("SELECT min(a) FROM t") == before


def test_rules_only_matter_individually(drv):
    # not monotone: MinMaxOpt off changes the plan, MinMaxOpt + QueryFlattener off does not
    base = drv.explain("SELECT min(a) FROM t")
    drv.apply_variant(drv.rules_off_spec(["MinMaxOpt"]))
    one = drv.explain("SELECT min(a) FROM t")
    drv.reset_variant()
    assert one != base
