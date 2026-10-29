# wrong_result: result differs under plan variant index_scans: 0 rows by default, 1 rows with variant

* Oracle: **plan-variant**, signature `b0171fcfb39a`
* Reproduced: 0/3 on ?
* Reduced: 1 -> ? statements, 10 -> ? tokens
* Verdict: flaky

## Reproducer

```sql
-- pgfuzz triage of b0171fcfb39a: wrong_result via plan-variant
-- default plan:
SELECT c0 FROM tl WHERE (c0 = 1);
-- plan variant index_scans (must return the same rows):
SET enable_seqscan = 'off';
SET enable_bitmapscan = 'off';
SELECT c0 FROM tl WHERE (c0 = 1);
RESET enable_seqscan;
RESET enable_bitmapscan;
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
