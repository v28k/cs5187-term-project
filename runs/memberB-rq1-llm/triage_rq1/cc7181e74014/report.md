# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `cc7181e74014`
* Reproduced: 2/3 on 20devel
* Reduced: 2 -> 1 statements, 174 -> 47 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of cc7181e74014: assertion via assertion
SELECT 'c4ca4238a0b923820dcc509a6f75849b' FROM (JSON_TABLE (TO_JSONB (ROW ('2024-01-01 00:00:00+00', '1 year 2 mons 3 days 04:05:06.789'::interval) <= ROW ('2024-01-06 15:00:00+00'::timestamptz, '70:00:00'::interval)), '$.a[*]' COLUMNS (c0 FOR ORDINALITY)) AS a1 FULL JOIN v0 AS a2 ON NULL);
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
ExecInitAppend
ExecInitNode
ExecInitSort
ExecInitNode
standard_ExecutorStart
ExecutorStart
PortalStart
PostgresMain
postmaster_child_launch
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
