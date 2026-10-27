# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `cde9712bc8db`
* Reproduced: 3/3 on 20devel
* Reduced: 3 -> 1 statements, 302 -> 60 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of cde9712bc8db: assertion via assertion
WITH rc(c0) AS (SELECT 1) SELECT FROM (t1 CROSS JOIN JSON_TABLE (CASE WHEN TRUE THEN CASE WHEN (ROW (11, '{"k": 1}') <= ROW (41, '0'::text)) THEN '{"k": 2, "a": [0]}'::jsonb END END, '$[*]' COLUMNS ( c1 text PATH '$')) AS a2);
```

## Assertion

`TRAP: failed Assert("list_length(rcexpr->inputcollids) == nopers"), File: "execExpr.c", Line: 2078`

## Backtrace (top frames)

```
ExceptionalCondition
ExecInitExpr
ExecInitTableFuncScan
ExecInitNode
ExecInitNestLoop
ExecInitNode
ExecInitSort
ExecInitNode
ExecInitAgg
ExecInitNode
standard_ExecutorStart
PortalStart
PostgresMain
BackendMain
postmaster_child_launch
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
