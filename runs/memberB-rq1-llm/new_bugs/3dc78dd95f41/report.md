# internal_error: SubPlan found with no parent plan

* Oracle: **internal_error**, signature `3dc78dd95f41`
* Reproduced: 3/3 on 20devel
* Reduced: 4 -> 1 statements, 253 -> 62 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 3dc78dd95f41: internal_error via internal_error
MERGE INTO tp a1 USING (SELECT TRUE AS c1 LIMIT 1) AS a2 ON (c0 IS NULL) WHEN MATCHED THEN UPDATE SET c1 = NULLIF (a1.c1, CONCAT ((SELECT NULL WHERE a2.c1))) WHEN NOT MATCHED THEN INSERT (c0, c1) VALUES ( 1, 'x%');
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
