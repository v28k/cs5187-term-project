# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `cc7181e74014`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 193 -> 53 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of cc7181e74014: assertion via assertion
SELECT FROM (JSON_TABLE (CASE WHEN ( (500, 10::bigint) <= ROW (2, NULL::bigint)) THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb ELSE '{"k": 0, "a": [3, 4, 5]}'::jsonb END, '$[*]' COLUMNS (c0 int PATH '$.k')) AS a1 JOIN t4 AS a2 ON TRUE);
```

## Assertion

`TRAP: failed Assert("list_length(rcexpr->inputcollids) == nopers"), File: "execExpr.c", Line: 2078`

## Backtrace (top frames)

```
ExceptionalCondition
ExecInitExpr
ExecInitTableFuncScan
ExecInitNode
ExecInitHashJoin
ExecInitNode
ExecInitAgg
ExecInitNode
standard_ExecutorStart
PortalStart
PostgresMain
BackendMain
postmaster_child_launch
PostmasterMain
main
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
