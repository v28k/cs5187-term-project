# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `448f485d72d5`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 138 -> 26 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 448f485d72d5: assertion via assertion
SELECT FROM t4 a1 WHERE (c0 <> ANY (SELECT a1.c1 UNION ALL SELECT a1.c0 FROM v0) AND FALSE);
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
standard_planner
planner
pg_plan_query
pg_plan_queries
PostgresMain
BackendMain
postmaster_child_launch
PostmasterMain
main
__libc_start_main
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
