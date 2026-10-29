# internal_error: could not find pathkey item to sort

* Oracle: **internal_error**, signature `4fedb431a765`
* Reproduced: 3/3 on 20devel
* Reduced: 3 -> 1 statements, 180 -> 170 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 4fedb431a765: internal_error via internal_error
SELECT a3.c1 AS c0, CASE WHEN TRUE THEN NULL::bigint ELSE 1000::bigint END AS c1, RANGE_MERGE ('[0,0]'::int4range, '[1,10)'::int4range) AS c2 FROM (t0 AS a1 JOIN (t0 AS a2 JOIN tl AS a3 ON ((a2.c0 = a3.c0) AND FALSE)) ON (a1.c1 = a3.c1)) UNION ALL (SELECT DISTINCT a4.c1 AS c0, 100::bigint, COALESCE (int4range(2, 40), '[1,10)'::int4range) AS c2 FROM tl AS a4 INTERSECT ALL SELECT '{"k": 1}'::text AS c0, COUNT (*) AS c1, '[1,10)'::int4range AS c2 FROM ti AS a5, LATERAL (SELECT 1 AS c0 FROM ti AS a6 WHERE TRUE GROUP BY a6.c1, a6.c0) AS a7 WHERE FALSE GROUP BY a5.c0, a7.c0);
```

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
