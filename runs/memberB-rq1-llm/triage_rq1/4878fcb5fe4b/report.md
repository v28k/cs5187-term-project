# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `4878fcb5fe4b`
* Reproduced: 3/3 on 20devel
* Reduced: 1 -> 1 statements, 163 -> 43 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 4878fcb5fe4b: assertion via assertion
SELECT FROM JSON_TABLE (CASE WHEN ( (1.0::float8, '_'::text) > ROW ('50', 'A') AND NULL) THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb END, '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
```

## Assertion

`TRAP: failed Assert("list_length(rcexpr->inputcollids) == nopers"), File: "execExpr.c", Line: 2078`

## Backtrace (top frames)

```
ExceptionalCondition
ExecInitExpr
ExecInitTableFuncScan
ExecInitNode
ExecInitAppend
ExecInitNode
ExecInitAgg
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
