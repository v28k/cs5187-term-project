# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `83bdce4a0403`
* Reproduced: 3/3 on 20devel
* Reduced: 3 -> 1 statements, 118 -> 18 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 83bdce4a0403: assertion via assertion
SELECT FROM t3 WHERE (c5 IN (SELECT c5 FROM v0 UNION ALL SELECT c5));
```

## Assertion

`TRAP: failed Assert("var->varno == rel->relid"), File: "pathkeys.c", Line: 1268`

## Backtrace (top frames)

```
ExceptionalCondition
convert_subquery_pathkeys
make_one_rel
query_planner
subquery_planner
plan_set_operations
subquery_planner
standard_planner
planner
pg_plan_query
pg_plan_queries
PostgresMain
BackendMain
postmaster_child_launch
PostmasterMain
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
