# internal_error: corrupt MVNDistinct entry

* Oracle: **metamorphic:expr**, signature `84e36fe21cff`
* Reproduced: 3/3 on 20devel
* Reduced: 5 -> 3 statements, 128 -> 24 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 84e36fe21cff: internal_error via metamorphic:expr
CREATE STATISTICS (NDISTINCT) ON c0, c1 FROM ti;
ANALYZE ti;
-- the two queries below must return the same rows (as a multiset):
SELECT NULL FROM ti a1, LATERAL (SELECT a1.c0) a2 GROUP BY ROLLUP (a1.c0, a2);
SELECT NULL FROM ti a1, LATERAL (SELECT (SELECT (a1.c0))) a2 GROUP BY ROLLUP (a1.c0, a2);
```

## Observed on the test server

`lhs`:

```
    ERROR: XX000 corrupt MVNDistinct entry
```

`rhs`:

```
    ERROR: XX000 corrupt MVNDistinct entry
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
