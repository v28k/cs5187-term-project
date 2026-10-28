# wrong_result: metamorphic check rls failed: 1 rows vs 1 rows

* Oracle: **metamorphic:rls**, signature `82444bc96f83`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 103 -> 2 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 82444bc96f83: wrong_result via metamorphic:rls
-- the two queries below must return the same rows (as a multiset):
VALUES ((SQRT (ABS ((SELECT SUM (10.0::float8) FROM t4 AS a1 WHERE FALSE))) + (0)::float8), (10 + LENGTH (''::text)), (SELECT JSONB_AGG ((SELECT SUM (a4.c0) FROM t1 AS a4 WHERE TRUE) ORDER BY (SELECT SUM (a4.c0) FROM t1 AS a4 WHERE TRUE)) FROM (t3 AS a2 FULL JOIN ti AS a3 ON (a2.c0 = a3.c0))));
VALUES ((SQRT (ABS ((SELECT SUM (10.0::float8) FROM t4 AS a1 WHERE FALSE))) + (0)::float8), (10 + LENGTH (''::text)), (SELECT JSONB_AGG ((SELECT SUM (a4.c0) FROM t1 AS a4 WHERE TRUE) ORDER BY (SELECT SUM (a4.c0) FROM t1 AS a4 WHERE TRUE)) FROM ((SELECT * FROM t3 WHERE (c1 IS NOT FALSE)) AS a2 FULL JOIN (SELECT * FROM ti WHERE (c1 IS DISTINCT FROM 'a')) AS a3 ON (a2.c0 = a3.c0))));
```

## Observed on the test server

`lhs`:

```
    NULL | 10 | [1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275]
```

`rhs`:

```
    NULL | 10 | [1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275, 1275]
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
