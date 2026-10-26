# wrong_result: result differs under plan variant xversion: 30 rows by default, 30 rows with variant

* Oracle: **cross-version**, signature `686d5e233140`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 4 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of 686d5e233140: wrong_result via cross-version
SELECT * FROM t2;
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
