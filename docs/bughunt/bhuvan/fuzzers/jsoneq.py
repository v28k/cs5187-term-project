"""json vs jsonb constructor equivalence sweep.

For every value v (many types, incl. NULL/NaN/Infinity/arrays/composites/domains)
and every pair of equivalent constructors F_json / F_jsonb, check
    F_json(...)::jsonb  IS NOT DISTINCT FROM  F_jsonb(...)
usage: jsoneq.py PORT
"""
import sys, itertools
import psycopg

VALUES = [
 "NULL::int", "1", "'1.50'::numeric", "'NaN'::numeric", "'Infinity'::numeric", "'-Infinity'::float8", "'NaN'::float4",
 "1e300::float8", "'-0'::float8", "123456789012345678901234567890::numeric", "true", "'a\"b\\c'::text", "''::text",
 "E'\\u0001'::text", "'null'::text", "'2000-01-01'::date", "'infinity'::date", "'2000-01-01 12:00'::timestamp",
 "'2000-01-01 12:00+05:30'::timestamptz", "'-infinity'::timestamptz", "'12:00'::time", "'12:00+01'::timetz",
 "'1 day 2 hours'::interval", "'infinity'::interval", "'\\x00ff'::bytea", "ARRAY[1,NULL,3]", "ARRAY[[1,2],[3,4]]",
 "'{}'::int[]", "ARRAY[NULL]::int[]", "'[1:2]={5,6}'::int[]", "ROW(1, NULL, 'x')", "ROW(NULL, NULL)",
 "'{\"a\": null}'::jsonb", "'null'::jsonb", "'[1, null]'::json", "'\"s\"'::json", "'{\"a\":1, \"a\":2}'::json",
 "'1.0'::json", "'1e2'::jsonb", "'(1,2)'::point", "'[1,3)'::int4range", "'empty'::numrange", "'{[1,2)}'::int4multirange",
 "'a'::\"char\"", "'abc'::name", "'1.2.3.4'::inet", "'00000000-0000-0000-0000-000000000000'::uuid",
 "'<a>x</a>'::xml", "'a b'::tsvector", "12.5::money", "'x'::dj", "ROW(1.0, ARRAY['a',NULL])::cj", "'{\"k\":[1,{\"z\":null}]}'::jsonb",
 "'red'::ej", "ARRAY[ROW(1,'a')::cj2]", "'{\"(1,a)\"}'::cj2[]", "B'101'", "'0/16'::pg_lsn",
]

PAIRS = [
 ("to_json({v})", "to_jsonb({v})"),
 ("json_build_array({v}, {v})", "jsonb_build_array({v}, {v})"),
 ("json_build_object('k', {v})", "jsonb_build_object('k', {v})"),
 ("(SELECT json_agg(x) FROM (VALUES ({v}), ({v})) t(x))", "(SELECT jsonb_agg(x) FROM (VALUES ({v}), ({v})) t(x))"),
 ("(SELECT json_agg(x) FILTER (WHERE x IS NOT NULL) FROM (VALUES ({v})) t(x))", "(SELECT jsonb_agg(x) FILTER (WHERE x IS NOT NULL) FROM (VALUES ({v})) t(x))"),
 ("(SELECT json_object_agg('k', x) FROM (VALUES ({v})) t(x))", "(SELECT jsonb_object_agg('k', x) FROM (VALUES ({v})) t(x))"),
 ("(SELECT json_agg_strict(x) FROM (VALUES ({v}), (NULL)) t(x))", "(SELECT jsonb_agg_strict(x) FROM (VALUES ({v}), (NULL)) t(x))"),
 ("(SELECT json_object_agg_strict('k', x) FROM (VALUES ({v})) t(x))", "(SELECT jsonb_object_agg_strict('k', x) FROM (VALUES ({v})) t(x))"),
 ("(SELECT json_object_agg_unique('k', x) FROM (VALUES ({v})) t(x))", "(SELECT jsonb_object_agg_unique('k', x) FROM (VALUES ({v})) t(x))"),
 ("(SELECT json_object_agg_unique_strict('k', x) FROM (VALUES ({v})) t(x))", "(SELECT jsonb_object_agg_unique_strict('k', x) FROM (VALUES ({v})) t(x))"),
 ("JSON_OBJECT('k': {v} RETURNING json)", "JSON_OBJECT('k': {v} RETURNING jsonb)"),
 ("JSON_OBJECT('k': {v} ABSENT ON NULL RETURNING json)", "JSON_OBJECT('k': {v} ABSENT ON NULL RETURNING jsonb)"),
 ("JSON_OBJECT('k': {v} WITH UNIQUE KEYS RETURNING json)", "JSON_OBJECT('k': {v} WITH UNIQUE KEYS RETURNING jsonb)"),
 ("JSON_ARRAY({v}, {v} RETURNING json)", "JSON_ARRAY({v}, {v} RETURNING jsonb)"),
 ("JSON_ARRAY({v}, {v} NULL ON NULL RETURNING json)", "JSON_ARRAY({v}, {v} NULL ON NULL RETURNING jsonb)"),
 ("JSON_ARRAY(SELECT x FROM (VALUES ({v})) t(x) RETURNING json)", "JSON_ARRAY(SELECT x FROM (VALUES ({v})) t(x) RETURNING jsonb)"),
 ("(SELECT JSON_ARRAYAGG(x RETURNING json) FROM (VALUES ({v}), ({v})) t(x))", "(SELECT JSON_ARRAYAGG(x RETURNING jsonb) FROM (VALUES ({v}), ({v})) t(x))"),
 ("(SELECT JSON_ARRAYAGG(x NULL ON NULL RETURNING json) FROM (VALUES ({v})) t(x))", "(SELECT JSON_ARRAYAGG(x NULL ON NULL RETURNING jsonb) FROM (VALUES ({v})) t(x))"),
 ("(SELECT JSON_OBJECTAGG('k': x RETURNING json) FROM (VALUES ({v})) t(x))", "(SELECT JSON_OBJECTAGG('k': x RETURNING jsonb) FROM (VALUES ({v})) t(x))"),
 ("(SELECT JSON_OBJECTAGG('k': x ABSENT ON NULL RETURNING json) FROM (VALUES ({v})) t(x))", "(SELECT JSON_OBJECTAGG('k': x ABSENT ON NULL RETURNING jsonb) FROM (VALUES ({v})) t(x))"),
 ("JSON_SCALAR({v})", "JSON_SCALAR({v})::jsonb"),
 ("JSON({v}::text)", "{v}::text::jsonb"),
 ("row_to_json(ROW({v}, 1))", "to_jsonb(ROW({v}, 1))"),
 ("array_to_json(ARRAY[{v}])", "to_jsonb(ARRAY[{v}])"),
 ("(SELECT json_agg(t) FROM (SELECT {v} AS c) t)", "(SELECT jsonb_agg(t) FROM (SELECT {v} AS c) t)"),
]


def main():
    port = int(sys.argv[1])
    conn = psycopg.connect(f"host=/tmp port={port} user=postgres dbname=postgres", autocommit=True)
    conn.prepare_threshold = None
    cur = conn.cursor()
    for ddl in ["DROP DOMAIN IF EXISTS dj CASCADE", "CREATE DOMAIN dj AS text CHECK (VALUE <> '')",
                "DROP TYPE IF EXISTS cj CASCADE", "CREATE TYPE cj AS (n numeric, a text[])",
                "DROP TYPE IF EXISTS cj2 CASCADE", "CREATE TYPE cj2 AS (i int, t text)",
                "DROP TYPE IF EXISTS ej CASCADE", "CREATE TYPE ej AS ENUM ('red')"]:
        cur.execute(ddl)
    n = bad = errs = 0
    for v in VALUES:
        for fj, fb in PAIRS:
            a, b = fj.format(v=v), fb.format(v=v)
            ra = rb = None
            try:
                cur.execute(f"SELECT ({a})::text"); ra = ("ok", cur.fetchone()[0])
            except psycopg.Error as e:
                ra = ("err", e.sqlstate, str(e).splitlines()[0])
            try:
                cur.execute(f"SELECT ({b})::text"); rb = ("ok", cur.fetchone()[0])
            except psycopg.Error as e:
                rb = ("err", e.sqlstate, str(e).splitlines()[0])
            n += 1
            if ra[0] == "ok" and rb[0] == "ok":
                cur.execute("SELECT %s::jsonb IS NOT DISTINCT FROM %s::jsonb", (ra[1], rb[1])) if ra[1] is not None and rb[1] is not None else None
                same = (ra[1] is None and rb[1] is None) or (ra[1] is not None and rb[1] is not None and cur.fetchone()[0])
                if not same:
                    bad += 1
                    print(f"DIFF  v={v}\n   json : {a}\n          -> {ra[1]}\n   jsonb: {b}\n          -> {rb[1]}")
            elif ra[0] != rb[0] or (ra[0] == 'err' and ra[1] != rb[1]):
                errs += 1
                print(f"ERRDIFF v={v}\n   json : {a} -> {ra}\n   jsonb: {b} -> {rb}")
    print(f"checked={n} value_diffs={bad} error_diffs={errs}")


if __name__ == "__main__":
    main()
