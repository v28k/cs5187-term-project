# wrong_result: result differs under plan variant partitionwise: 30 rows by default, 30 rows with variant

* Oracle: **plan-variant**, signature `c5a5ed497011`
* Reproduced: 3/3 on 20devel
* Reduced: 3 -> 1 statements, 220 -> 15 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of c5a5ed497011: wrong_result via plan-variant
-- default plan:
(SELECT CORR (1.0 / 3,1.0 / 3) FROM tl);
-- plan variant partitionwise (must return the same rows):
SET enable_partitionwise_join = 'on';
SET enable_partitionwise_aggregate = 'on';
(SELECT CORR (1.0 / 3,1.0 / 3) FROM tl);
RESET enable_partitionwise_join;
RESET enable_partitionwise_aggregate;
```

## Observed on the test server

`query`:

```
    NULL
```

## Where the bug is (localization)

**planner**: the answer depends on planner settings: parallel, partitionwise; the code paths these switch are the first suspects.

Settings and the code they switch:

* `debug_parallel_query`: executor/execParallel.c, nodeGather.c
* `enable_partitionwise_aggregate`: optimizer/plan/planner.c (partitionwise aggregate)
* `enable_partitionwise_join`: optimizer/path/joinrels.c (partitionwise join)

| plan variant | answer changes | 
|---|---|---|---|
| nestloop_only | no |
| hashjoin_only | no |
| mergejoin_only | no |
| no_hashagg | no |
| no_sort_opt | no |
| index_scans | no |
| seq_scans | no |
| no_memoize_material | no |
| parallel | yes |
| partitionwise | yes |
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
