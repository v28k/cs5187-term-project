# wrong_result: result differs under plan variant no_hashagg: 40 rows by default, 40 rows with variant

* Oracle: **plan-variant**, signature `294a0263ac67`
* Reproduced: 3/3 on 20devel
* Reduced: 2 -> 1 statements, 64 -> 23 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 294a0263ac67: wrong_result via plan-variant
-- default plan:
SELECT a1.c3, 0 FROM (t3 a1 LEFT JOIN t4 ON NULL) UNION SELECT '7 days', c1 FROM t4;
-- plan variant no_hashagg (must return the same rows):
SET enable_hashagg = 'off';
SELECT a1.c3, 0 FROM (t3 a1 LEFT JOIN t4 ON NULL) UNION SELECT '7 days', c1 FROM t4;
RESET enable_hashagg;
```

## Observed on the test server

`query`:

```
    7 days | 22
    392:00:00 | 0
    329:00:00 | 0
    252:00:00 | 0
    539:00:00 | 0
    35:00:00 | 0
    420:00:00 | 0
    7 days | 54
    259:00:00 | 0
    497:00:00 | 0
    168:00:00 | 0
    532:00:00 | 0
    56:00:00 | 0
    567:00:00 | 0
    609:00:00 | 0
    427:00:00 | 0
    322:00:00 | 0
    301:00:00 | 0
    133:00:00 | 0
    595:00:00 | 0
    448:00:00 | 0
    49:00:00 | 0
    7 days | 50
    7 days | 26
    7 days | 44
    455:00:00 | 0
    7 days | 6
    7 days | 58
    434:00:00 | 0
    413:00:00 | 0
    ... (131 rows)
```

## Where the bug is (localization)

**planner**: the answer depends on planner settings: no_hashagg; the code paths these switch are the first suspects.

Settings and the code they switch:

* `enable_hashagg`: executor/nodeAgg.c (hash), optimizer/plan/planner.c

| plan variant | answer changes | 
|---|---|---|---|
| nestloop_only | no |
| hashjoin_only | no |
| mergejoin_only | no |
| no_hashagg | yes |
| no_sort_opt | no |
| index_scans | no |
| seq_scans | no |
| no_memoize_material | no |
| parallel | no |
| partitionwise | no |
| no_partition_pruning | no |
| geqo | no |
| no_join_reorder | no |
| tiny_work_mem | no |
| no_reordering | no |
| no_self_join_elim | no |
| no_eager_agg | no |
| jit | no |

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
