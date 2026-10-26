# wrong_result: result differs under plan variant xversion: 378 rows by default, 189 rows with variant

* Oracle: **cross-version**, signature `886c0db769c0`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 22 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of 886c0db769c0: wrong_result via cross-version
SELECT a.c1 FROM t0 AS a JOIN t1 AS b ON (a.c0 = b.c0);
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
