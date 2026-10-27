# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `68e520951660`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 181 -> 57 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 68e520951660: assertion via assertion
SELECT ARRAY[1] FROM JSON_TABLE ( ( JSONB_BUILD_ARRAY ( (CASE WHEN FALSE THEN TRUE ELSE (ROW ('{"k": -1, "a": [1, 2, 3]}'::jsonb, NULL::int) <= ROW ('{"k": 0, "a": [3, 4, 5]}', 16)) END AND TRUE))) - 'k', '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
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
PortalStart
PostgresMain
BackendMain
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
