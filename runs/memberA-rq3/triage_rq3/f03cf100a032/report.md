# wrong_result: result differs under plan variant no_eager_agg: 0 rows by default, 80 rows with variant

* Oracle: **plan-variant**, signature `f03cf100a032`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 5 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of f03cf100a032: wrong_result via plan-variant
-- default plan:
SELECT * FROM tl LIM;
-- plan variant no_eager_agg (must return the same rows):
SET enable_eager_aggregate = 'off';
SELECT * FROM tl LIM;
RESET enable_eager_aggregate;
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
