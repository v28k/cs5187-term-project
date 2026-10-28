# assertion: server connection lost while running metamorphic check tlp_where

* Oracle: **metamorphic:tlp_where**, signature `8a4e039bb76f`
* Reproduced: 3/3 on 20devel
* Reduced: 1 -> 1 statements, 219 -> 2 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 8a4e039bb76f: assertion via metamorphic:tlp_where
-- the two queries below must return the same rows (as a multiset):
WITH cte1 AS (SELECT ((100::bigint % 1000) << 1) AS c0 FROM ti AS a1), cte2 AS MATERIALIZED (SELECT SUM (((10.0::numeric % 100) * (2.25::numeric % 100))) OVER (PARTITION BY 1.5::numeric, 0 ORDER BY '7 days'::interval NULLS LAST, 3) AS c0 FROM (SELECT '2024-01-01 00:00:00+00'::timestamptz AS c0, '16.333333333333332'::float8 AS c1 FROM t3 AS a2 WHERE a2.c1) AS a3 WHERE (''::text IS JSON)) SELECT (JSONB_BUILD_OBJECT ('k', 100, 'a', JSONB_BUILD_ARRAY ('0x'::text, '50'::float8)) - 'k') AS c0 FROM (SELECT '{}'::text[] AS c0 FROM cte1 AS a4) AS a5 UNION ALL SELECT JSONB_INSERT (JSONB_BUILD_OBJECT ('k', '%'::text, 'a', JSONB_BUILD_ARRAY ('{NULL}'::text[], a7.c0)), '{a,0}', '{"k": 1, "a": [1, 2]}'::jsonb) AS c0 FROM (SELECT 'é'::text AS c0, 10 AS c1, '3'::bigint AS c2 FROM cte2 AS a6) AS a7;
WITH cte1 AS (((SELECT ((100::bigint % 1000) << 1) AS c0 FROM ti AS a1 WHERE (('[1,10)'::int4range <= '[1,10)'::int4range))) UNION ALL (SELECT ((100::bigint % 1000) << 1) AS c0 FROM ti AS a1 WHERE NOT (('[1,10)'::int4range <= '[1,10)'::int4range))) UNION ALL (SELECT ((100::bigint % 1000) << 1) AS c0 FROM ti AS a1 WHERE (('[1,10)'::int4range <= '[1,10)'::int4range)) IS NULL))), cte2 AS MATERIALIZED (SELECT SUM (((10.0::numeric % 100) * (2.25::numeric % 100))) OVER (PARTITION BY 1.5::numeric, 0 ORDER BY '7 days'::interval NULLS LAST, 3) AS c0 FROM (SELECT '2024-01-01 00:00:00+00'::timestamptz AS c0, '16.333333333333332'::float8 AS c1 FROM t3 AS a2 WHERE a2.c1) AS a3 WHERE (''::text IS JSON)) SELECT (JSONB_BUILD_OBJECT ('k', 100, 'a', JSONB_BUILD_ARRAY ('0x'::text, '50'::float8)) - 'k') AS c0 FROM (SELECT '{}'::text[] AS c0 FROM cte1 AS a4) AS a5 UNION ALL SELECT JSONB_INSERT (JSONB_BUILD_OBJECT ('k', '%'::text, 'a', JSONB_BUILD_ARRAY ('{NULL}'::text[], a7.c0)), '{a,0}', '{"k": 1, "a": [1, 2]}'::jsonb) AS c0 FROM (SELECT 'é'::text AS c0, 10 AS c1, '3'::bigint AS c2 FROM cte2 AS a6) AS a7;
```

## Assertion

`TRAP: failed Assert("!parallel_aware || pathnode->path.parallel_safe"), File: "pathnode.c", Line: 1437`

## Backtrace (top frames)

```
ExceptionalCondition
create_append_path
add_paths_to_append_rel
make_one_rel
query_planner
subquery_planner
standard_planner
planner
pg_plan_query
pg_plan_queries
PostgresMain
postmaster_child_launch
PostmasterMain
main
__libc_start_main
```

## Observed on the test server

`lhs`:

```
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    {"a": ["0x", 50]}
    ... (46 rows)
```

`rhs`:

```
    ERROR: None consuming input failed: server closed the connection unexpectedly
	This probably means the server terminated abnormally
	before or while processing the request.
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
