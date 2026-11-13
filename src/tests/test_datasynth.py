"""Constraint-based data synthesis (C3): predicate parsing, Z3 encoding, generated rows."""

import pytest

pytest.importorskip("z3")

from pgfuzz.datasynth import DataSynth, alias_map, parse_predicate  # noqa: E402
from pgfuzz.grammar.schema import schema_from_dict  # noqa: E402

SCHEMA = schema_from_dict({"relations": {
    "t0": {"columns": [["c0", "int"], ["c1", "text"], ["c2", "float8"]]},
    "t1": {"columns": [["c0", "int", "pk", "notnull"], ["c1", "int"]]},
    "t3": {"columns": [["c0", "int", "notnull"], ["c1", "bool"], ["c2", "date"]]},
    "v0": {"kind": "view", "columns": [["c0", "int"]]},
}})


def _eval(pred: str, row: dict[str, str]):
    """Evaluate ``pred`` on one row with SQLite (three-valued, like the target engines)."""
    import sqlite3

    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE r (c0, c1, c2)")
    cols = ", ".join(row)
    db.execute(f"INSERT INTO r ({cols}) VALUES ({', '.join(row.values())})")
    return db.execute(f"SELECT ({pred}) FROM r").fetchone()[0]


def test_parse_shapes():
    assert parse_predicate("a1.c0 > 5") == ("op", ">", ("col", "a1", "c0"), ("lit", "int", 5))
    t = parse_predicate("x BETWEEN 1 AND 2 OR y IS NOT NULL")
    assert t[0] == "op" and t[1] == "OR" and t[2][0] == "between" and t[3] == ("isnull", ("col", None, "y"), True)
    assert parse_predicate("c IN (1, 2)")[0] == "in"
    assert parse_predicate("COALESCE(a.c0, 1) = 2")[2][0] == "call"
    assert parse_predicate("CASE WHEN a.c0 > 1 THEN TRUE ELSE FALSE END")[0] == "case"
    assert parse_predicate("EXISTS (SELECT 1)") == ("opaque",)
    assert parse_predicate("'5'::int > 3")[2] == ("cast", ("lit", "str", "5"), "int")


def test_alias_map_only_writable_tables():
    m = alias_map("SELECT 1 FROM t0 AS a1 JOIN v0 AS a2 ON TRUE, t1", SCHEMA)
    assert m == {"a1": "t0", "t1": "t1"}


@pytest.mark.parametrize("pred", [
    "a1.c0 > 5 AND a1.c1 LIKE 'ab%'",
    "a1.c0 BETWEEN 3 AND 7 OR a1.c1 IS NULL",
    "COALESCE(a1.c0, 5) > 3",
    "NOT (a1.c0 IN (1, 2, NULL))",
    "CASE WHEN a1.c0 > 2 THEN a1.c1 = 'x' ELSE a1.c2 < 1.5 END",
    "NULLIF(a1.c0, 3) = 3",
])
def test_rows_hit_the_intended_partitions(pred):
    """Every row the solver returns makes the predicate TRUE, FALSE or NULL as intended,
    checked by actually evaluating the predicate on that row."""
    ds = DataSynth(SCHEMA)
    rows = ds.rows(pred, "SELECT * FROM t0 AS a1")
    assert rows, pred
    outcomes = set()
    for table, cols in rows:
        assert table == "t0"
        v = _eval(pred.replace("a1.", ""), cols)
        outcomes.add(None if v is None else bool(v))
    # the solver solves TRUE, FALSE, NULL in that order and skips unsatisfiable ones
    assert len(outcomes) == len(rows)


def test_keys_are_distinct_and_away_from_seeded_rows():
    ds = DataSynth(SCHEMA)
    stmts = ds.inserts("a1.c0 > a1.c1", "SELECT * FROM t1 AS a1")
    keys = [int(s.split("VALUES (")[1].split(",")[0]) for s in stmts]
    assert len(stmts) == 2                     # TRUE and NULL (c1 NULL); FALSE needs c0 <= c1 <= 40
    assert len(set(keys)) == len(keys) and all(1000 <= k <= 1999 for k in keys)


def test_required_columns_are_filled_and_constant_predicates_still_give_rows():
    ds = DataSynth(SCHEMA)
    stmts = ds.inserts("TRUE", "SELECT * FROM t3 AS a1")
    assert stmts and all(s.startswith("INSERT INTO t3 (") and "c0" in s for s in stmts)


def test_unknown_columns_are_unconstrained():
    ds = DataSynth(SCHEMA)
    assert ds.rows("f(zz) > 1", "SELECT 1") == []
    assert ds.stats["unsupported"] == 1
