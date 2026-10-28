# wrong_result: metamorphic check rls failed: 8 rows vs 8 rows

* Oracle: **metamorphic:rls**, signature `015482844f3d`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 123 -> 2 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 015482844f3d: wrong_result via metamorphic:rls
-- the two queries below must return the same rows (as a multiset):
SELECT ARRAY_AGG ((SELECT PERCENTILE_DISC (0.5) WITHIN GROUP (ORDER BY a2.c0) FROM tp AS a2) ORDER BY (SELECT PERCENTILE_DISC (0.5) WITHIN GROUP (ORDER BY a2.c0) FROM tp AS a2)) AS c0, '{"k": 1}'::text AS c1 FROM ti AS a1 WHERE GREATEST (TRUE, FALSE) GROUP BY GROUPING SETS ((a1.c0), (a1.c1), ()) UNION SELECT ARRAY_AGG (a3.c0 ORDER BY a3.c0) AS c0, 'é'::text AS c1 FROM tl AS a3 GROUP BY ROLLUP (a3.c1) ORDER BY 2 NULLS LAST;
SELECT ARRAY_AGG ((SELECT PERCENTILE_DISC (0.5) WITHIN GROUP (ORDER BY a2.c0) FROM tp AS a2) ORDER BY (SELECT PERCENTILE_DISC (0.5) WITHIN GROUP (ORDER BY a2.c0) FROM tp AS a2)) AS c0, '{"k": 1}'::text AS c1 FROM (SELECT * FROM ti WHERE (c1 IS DISTINCT FROM 'a')) AS a1 WHERE GREATEST (TRUE, FALSE) GROUP BY GROUPING SETS ((a1.c0), (a1.c1), ()) UNION SELECT ARRAY_AGG (a3.c0 ORDER BY a3.c0) AS c0, 'é'::text AS c1 FROM tl AS a3 GROUP BY ROLLUP (a3.c1) ORDER BY 2 NULLS LAST;
```

## Observed on the test server

`lhs`:

```
    {100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100} | {"k": 1}
    {100} | {"k": 1}
    {100,100} | {"k": 1}
    {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80} | é
    {1,5,9,13,17,21,25,29,33,37,41,45,49,53,57,61,65,69,73,77} | é
    {4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64,68,72,76,80} | é
    {3,7,11,15,19,23,27,31,35,39,43,47,51,55,59,63,67,71,75,79} | é
    {2,6,10,14,18,22,26,30,34,38,42,46,50,54,58,62,66,70,74,78} | é
```

`rhs`:

```
    {100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100} | {"k": 1}
    {100} | {"k": 1}
    {100,100} | {"k": 1}
    {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80} | é
    {1,5,9,13,17,21,25,29,33,37,41,45,49,53,57,61,65,69,73,77} | é
    {4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64,68,72,76,80} | é
    {3,7,11,15,19,23,27,31,35,39,43,47,51,55,59,63,67,71,75,79} | é
    {2,6,10,14,18,22,26,30,34,38,42,46,50,54,58,62,66,70,74,78} | é
```

## Where the bug is (localization)

**sides_agree_by_default**: the two sides agree on the reduced case under default settings (check the reduction).

| plan variant | answer changes | sides agree | 
|---|---|---|---|
| nestloop_only | no | yes |
| hashjoin_only | no | yes |
| mergejoin_only | no | yes |
| no_hashagg | no | yes |
| no_sort_opt | no | yes |
| index_scans | no | yes |
| seq_scans | no | yes |
| no_memoize_material | no | yes |
| parallel | no | yes |
| partitionwise | no | yes |
| no_partition_pruning | no | yes |
| geqo | no | yes |
| no_join_reorder | no | yes |
| tiny_work_mem | no | yes |
| no_reordering | no | yes |
| no_self_join_elim | no | yes |
| no_eager_agg | no | yes |
| jit | no | yes |

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
