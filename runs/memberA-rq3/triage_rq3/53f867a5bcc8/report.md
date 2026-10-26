# wrong_result: result differs under plan variant xversion: 2 rows by default, 1 rows with variant

* Oracle: **cross-version**, signature `53f867a5bcc8`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 10 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of 53f867a5bcc8: wrong_result via cross-version
SELECT c1 FROM t2 WHERE (c1 = 1.5);
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
