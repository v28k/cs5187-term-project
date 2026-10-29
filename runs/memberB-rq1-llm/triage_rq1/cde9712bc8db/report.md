# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `cde9712bc8db`
* Reproduced: 3/3 on 20devel
* Reduced: 1 -> 1 statements, 443 -> 57 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of cde9712bc8db: assertion via assertion
SELECT FROM t4, JSON_TABLE (JSONB_BUILD_ARRAY (CASE '{"k": 2, "a": [0]}'::jsonb WHEN '{"k": 0, "a": [3, 4, 5]}'::jsonb THEN FALSE WHEN '{"k": 2, "a": [0]}'::jsonb THEN ( ('2024-01-01'::date, 3) >= ROW ('2024-01-01'::date, 21)) ELSE FALSE END), '$[*]' COLUMNS ( c1 text PATH '$')) AS a2;
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
ExecInitWindowAgg
ExecInitNode
ExecInitSort
ExecInitNode
standard_ExecutorStart
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
