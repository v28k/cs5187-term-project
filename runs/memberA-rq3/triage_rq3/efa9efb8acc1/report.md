# assertion: consuming input failed: server closed the connection unexpectedly

* Oracle: **assertion**, signature `efa9efb8acc1`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 112 -> 27 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of efa9efb8acc1: assertion via assertion
VALUES ( NORMALIZE (TO_CHAR (CASE WHEN TRUE THEN 'NaN'::numeric ELSE 0.0::numeric END + 0.0::numeric, 'FM999990.00')));
```

## Assertion

`TRAP: failed Assert("(char *) p == VARDATA_ANY(input) + VARSIZE_ANY_EXHDR(input)"), File: "varlena.c", Line: 5535`

## Backtrace (top frames)

```
ExceptionalCondition
ExecScan
standard_ExecutorRun
PortalRun
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
