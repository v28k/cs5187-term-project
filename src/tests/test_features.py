from pathlib import Path

from pgfuzz.core.sqlsplit import split_statements
from pgfuzz.eval.features import FEATURE_IDS, StmtView, feature_pairs, features_of, statement_shape

SEEDS = Path(__file__).resolve().parents[1] / "corpus" / "seeds" / "basic.sql"


def test_catalog_ids_unique():
    assert len(FEATURE_IDS) == len(set(FEATURE_IDS))


def test_keywords_inside_literals_are_ignored():
    f = features_of("SELECT 'JOIN LATERAL OVER', \"UNION\" FROM t0 -- WINDOW\n /* EXCEPT */")
    assert "join:lateral" not in f and "window:over" not in f and "setop:union" not in f and "setop:except" not in f
    assert "stmt:select" in f


def test_dollar_quotes():
    f = features_of("CREATE FUNCTION f() RETURNS int LANGUAGE sql AS $body$ SELECT 1 UNION SELECT 2 $body$")
    assert "stmt:create_function" in f and "ddl:sql_function" in f and "setop:union" not in f


def test_cte_kind_resolution():
    assert StmtView.of("WITH a AS (SELECT 1) SELECT * FROM a").kind == "SELECT"
    assert StmtView.of("WITH a AS (SELECT 1) INSERT INTO t SELECT * FROM a").kind == "INSERT"


def test_specific_features():
    f = features_of("SELECT c0, sum(c2) OVER (ORDER BY c0 ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) FROM t0 LEFT JOIN t1 USING (c0)")
    assert {"window:over", "window:frame", "join:left", "join:using", "agg"} <= f
    assert "join:inner" not in f


def test_shape_abstracts_literals_and_identifiers():
    assert statement_shape("SELECT a, 'x' FROM t WHERE b = 3") == statement_shape("select zz, 'yy' from q where r = 99")


def test_pairs_exclude_statement_kinds():
    assert feature_pairs({"stmt:select", "where", "limit"}) == {("limit", "where")}


def test_seed_corpus_covers_most_of_catalog():
    seen = set()
    for s in split_statements(SEEDS.read_text(encoding="utf-8")):
        seen |= features_of(s)
    assert len(seen) / len(FEATURE_IDS) > 0.6


def test_split_statements():
    sql = "SELECT ';'; -- a; comment\nDO $$ BEGIN PERFORM 1; END $$; SELECT E'\\';' ; /* ; */ SELECT \"a;b\""
    assert split_statements(sql) == ["SELECT ';'", "DO $$ BEGIN PERFORM 1; END $$", "SELECT E'\\';'", 'SELECT "a;b"']
