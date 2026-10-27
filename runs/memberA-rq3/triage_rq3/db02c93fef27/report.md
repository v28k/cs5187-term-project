# wrong_result: metamorphic check tlp_where failed: 1 rows vs 1 rows

* Oracle: **metamorphic:tlp_where**, signature `db02c93fef27`
* Reproduced: 3/3 on 20devel
* Reduced: 3 -> 1 statements, 70 -> 2 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of db02c93fef27: wrong_result via metamorphic:tlp_where
-- the two queries below must return the same rows (as a multiset):
SELECT '7 days'::interval AS c0 FROM t4 AS a1 INTERSECT ALL SELECT a2.c3 AS c0 FROM t3 AS a2 GROUP BY a2.c2, a2.c3, a2.c5 ORDER BY 1, 1;
((SELECT '7 days'::interval AS c0 FROM t4 AS a1 WHERE (('6.333333333333333'::float8 IN (SELECT CASE WHEN FALSE THEN 1.0::float8 ELSE SQRT (ABS ('66.66666666666667'::float8)) END AS c0)))) UNION ALL (SELECT '7 days'::interval AS c0 FROM t4 AS a1 WHERE NOT (('6.333333333333333'::float8 IN (SELECT CASE WHEN FALSE THEN 1.0::float8 ELSE SQRT (ABS ('66.66666666666667'::float8)) END AS c0)))) UNION ALL (SELECT '7 days'::interval AS c0 FROM t4 AS a1 WHERE (('6.333333333333333'::float8 IN (SELECT CASE WHEN FALSE THEN 1.0::float8 ELSE SQRT (ABS ('66.66666666666667'::float8)) END AS c0))) IS NULL)) INTERSECT ALL SELECT a2.c3 AS c0 FROM t3 AS a2 GROUP BY a2.c2, a2.c3, a2.c5 ORDER BY 1, 1;
```

## Observed on the test server

`lhs`:

```
    7 days
```

`rhs`:

```
    168:00:00
```

## Where the bug is (localization)

**not_toggled_by_planner_settings**: no planner setting removes the disagreement: suspect an always-applied rewrite, constant folding, a planner support function, or expression evaluation.

| plan variant | answer changes | sides agree | 
|---|---|---|---|
| nestloop_only | no | no |
| hashjoin_only | no | no |
| mergejoin_only | no | no |
| no_hashagg | no | no |
| no_sort_opt | no | no |
| index_scans | no | no |
| seq_scans | no | no |
| no_memoize_material | no | no |
| parallel | no | no |
| partitionwise | no | no |
| no_partition_pruning | no | no |
| geqo | no | no |
| no_join_reorder | no | no |
| tiny_work_mem | no | no |
| no_reordering | no | no |
| no_self_join_elim | no | no |
| no_eager_agg | no | no |
| jit | no | no |

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
