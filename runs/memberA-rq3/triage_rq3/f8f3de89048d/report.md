# wrong_result: result differs under plan variant xversion: 19 rows by default, 19 rows with variant

* Oracle: **cross-version**, signature `f8f3de89048d`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 14 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of f8f3de89048d: wrong_result via cross-version
SELECT c0, count(*) AS n FROM t0 GROUP BY c0;
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
