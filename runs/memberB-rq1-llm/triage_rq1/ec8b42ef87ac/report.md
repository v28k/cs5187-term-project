# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `ec8b42ef87ac`
* Reproduced: 3/3 on 20devel
* Reduced: 1 -> 1 statements, 145 -> 54 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of ec8b42ef87ac: assertion via assertion
SELECT FROM JSON_TABLE (JSON_QUERY (JSONB_INSERT ( ( JSONB_BUILD_ARRAY ( (7, ARRAY[1]) >= ROW (16, '{1,2,3,4}'::int[]))), '{a,0}', '{"k": 1, "a": [1, 2]}'::jsonb), '$.a[1]'), '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
```

## Assertion

`TRAP: failed Assert("list_length(rcexpr->inputcollids) == nopers"), File: "execExpr.c", Line: 2078`

## Backtrace (top frames)

```
ExceptionalCondition
ExecInitExpr
ExecInitTableFuncScan
ExecInitNode
ExecInitAgg
ExecInitNode
standard_ExecutorStart
ExecutorStart
PortalStart
PostgresMain
postmaster_child_launch
PostmasterMain
main
__libc_start_main
_start
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
