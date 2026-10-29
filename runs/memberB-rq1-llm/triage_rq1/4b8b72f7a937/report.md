# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `4b8b72f7a937`
* Reproduced: 3/3 on 20devel
* Reduced: 3 -> 1 statements, 169 -> 40 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 4b8b72f7a937: assertion via assertion
SELECT FROM (t0 JOIN JSON_TABLE (JSON_ARRAY (ROW (33, 100.0) <= ROW (16, 42.5::numeric)), '$[*]' COLUMNS (c0 int PATH '$.k')) AS a2 ON TRUE);
```

## Assertion

`TRAP: failed Assert("list_length(rcexpr->inputcollids) == nopers"), File: "execExpr.c", Line: 2078`

## Backtrace (top frames)

```
ExceptionalCondition
ExecInitExpr
ExecInitTableFuncScan
ExecInitNode
ExecInitHash
ExecInitNode
ExecInitHashJoin
ExecInitNode
standard_ExecutorStart
ExecutorStart
PortalStart
PostgresMain
postmaster_child_launch
PostmasterMain
main
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
