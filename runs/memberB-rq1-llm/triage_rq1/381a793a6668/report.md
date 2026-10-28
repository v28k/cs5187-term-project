# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `381a793a6668`
* Reproduced: 3/3 on 20devel
* Reduced: 5 -> 1 statements, 126 -> 42 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 381a793a6668: assertion via assertion
SELECT FROM JSON_TABLE ( ( CASE WHEN ( (100.0, '0'::interval) >= (NULL::numeric, '00:00:00.000001'::interval)) THEN '{}' END), '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
```

## Assertion

`TRAP: failed Assert("list_length(rcexpr->inputcollids) == nopers"), File: "execExpr.c", Line: 2078`

## Backtrace (top frames)

```
ExceptionalCondition
ExecInitExpr
ExecInitTableFuncScan
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
