# internal_error: no relation entry for relid 1

* Oracle: **internal_error**, signature `c51c4dacc7f1`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 262 -> 68 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of c51c4dacc7f1: internal_error via internal_error
WITH rc(c0) AS (SELECT 1) SELECT '7 days' FROM LATERAL (SELECT COALESCE (MAX (c2)) AS c1 FROM t4 AS a2) AS a3 WHERE COALESCE (7 = ANY (ARRAY_CAT (CASE WHEN TRUE THEN ARRAY_POSITIONS (ARRAY[LENGTH (c1)], 21) ELSE ARRAY[1] END, '{}')));
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
