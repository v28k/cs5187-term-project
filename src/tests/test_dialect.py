from pgfuzz.grammar.dialect import Dialect

D = Dialect.from_data({"cast_style": "function", "cast_types": {"int": "INTEGER", "float8": "REAL", "text": "TEXT",
                                                             "numeric": "NUMERIC", "date": "TEXT"},
                       "functions": {"GREATEST": "MAX", "LEAST": "MIN"}})


def test_literal_and_parenthesised_casts():
    assert D.apply("SELECT 0.5::numeric") == "SELECT CAST(0.5 AS NUMERIC)"
    assert D.apply("SELECT (a1.c0 + 1)::float8") == "SELECT CAST((a1.c0 + 1) AS REAL)"
    assert D.apply("SELECT 'x'::text, NULL::int") == "SELECT CAST('x' AS TEXT), CAST(NULL AS INTEGER)"


def test_function_call_qualified_name_and_case():
    assert D.apply("SELECT ROUND(x, 2)::int") == "SELECT CAST(ROUND(x, 2) AS INTEGER)"
    assert D.apply("SELECT a1.c0::text") == "SELECT CAST(a1.c0 AS TEXT)"
    assert D.apply("SELECT CASE WHEN x THEN 1 ELSE 2 END::text") == "SELECT CAST(CASE WHEN x THEN 1 ELSE 2 END AS TEXT)"


def test_nested_casts_and_unknown_types_and_renames():
    assert D.apply("SELECT ((x)::int)::text") == "SELECT CAST((CAST((x) AS INTEGER)) AS TEXT)"
    assert D.apply("SELECT x::numeric(10, 2)") == "SELECT CAST(x AS NUMERIC)"
    assert D.apply("SELECT x::bigint") == "SELECT CAST(x AS bigint)"
    assert D.apply("SELECT GREATEST(1, LEAST(2, 3))") == "SELECT MAX(1, MIN(2, 3))"
    assert D.apply("SELECT (a IN (1, 2))") == "SELECT (a IN (1, 2))"


def test_inactive_dialect_is_identity():
    assert Dialect().apply("SELECT 1::int") == "SELECT 1::int"
