# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `ec8b42ef87ac`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 246 -> 66 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of ec8b42ef87ac: assertion via assertion
SELECT 100 FROM JSON_TABLE (JSONB_BUILD_ARRAY (100::bigint - CASE WHEN (CASE WHEN COALESCE (ROW ('2000-01-01'::date, 'NaN'::text) <= ROW ('2024-12-31'::date, '35'::text)) THEN 1::bigint END = 1) THEN NULL::bigint END), '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
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
