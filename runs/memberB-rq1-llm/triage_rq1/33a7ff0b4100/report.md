# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `33a7ff0b4100`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 131 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of 33a7ff0b4100: assertion via assertion
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) SELECT '{"k": 1, "a": [1, 2]}'::jsonb AS c0, 'A'::text AS c1, TRUE AS c2, CASE JSON_VALUE (JSON_OBJECT ('k' VALUE '-3 hours'::interval RETURNING jsonb), '$.a[*]') WHEN a1.c1 THEN 'ß'::text WHEN 'W'::text THEN CASE WHEN ('{"k": 1, "a": [1, 2]}'::jsonb <@ '{"k": 0, "a": [3, 4, 5]}'::jsonb) THEN ('{"k": 2, "a": [0]}'::jsonb ->> 0) ELSE COALESCE (a1.c1, a1.c1) END ELSE JSON_VALUE (JSON_ARRAY ('0'::int, 100 RETURNING jsonb), '$.a.size()') END AS c3 FROM tp AS a1 WHERE (a1.c0 = ALL (SELECT 10 AS c0 FROM t3 AS a2));
```

## Assertion

`TRAP: failed Assert("toc->toc_entry[i].key != key"), File: "shm_toc.c", Line: 190`

## Backtrace (top frames)

```
ExceptionalCondition
shm_toc_insert
ExecMaterialInitializeDSM
planstate_tree_walker_impl
planstate_tree_walker_impl
ExecInitParallelPlan
ExecProcNodeInstr
standard_ExecutorRun
ExecutorRun
ExplainOnePlan
standard_ExplainOneQuery
ExplainQuery
standard_ProcessUtility
ProcessUtility
PortalRun
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
