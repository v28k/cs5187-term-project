# wrong_result: result differs under plan variant index_scans: 1 rows by default, 1 rows with variant

* Oracle: **plan-variant**, signature `2c5e24d151f2`
* Reproduced: 3/3 on 20devel
* Reduced: 1 -> 1 statements, 637 -> 48 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 2c5e24d151f2: wrong_result via plan-variant
-- default plan:
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a2.c3)) - a2.c3 * 1)) FROM (t1 a1 JOIN t3 a2 ON (a1.c0 = a2.c0)) WHERE a2.c1;
-- plan variant index_scans (must return the same rows):
SET enable_seqscan = 'off';
SET enable_bitmapscan = 'off';
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a2.c3)) - a2.c3 * 1)) FROM (t1 a1 JOIN t3 a2 ON (a1.c0 = a2.c0)) WHERE a2.c1;
RESET enable_seqscan;
RESET enable_bitmapscan;
```

## Observed on the test server

`query`:

```
    00:00:00
```

## Where the bug is (localization)

**planner**: the answer depends on planner settings: mergejoin_only, index_scans; the code paths these switch are the first suspects.

Settings and the code they switch:

* `enable_bitmapscan`: executor/nodeBitmapHeapscan.c, optimizer/path/indxpath.c
* `enable_hashjoin`: executor/nodeHashjoin.c, optimizer/path/joinpath.c
* `enable_nestloop`: executor/nodeNestloop.c, optimizer/path/joinpath.c
* `enable_seqscan`: optimizer/path/indxpath.c, executor/nodeIndexscan.c

| plan variant | answer changes | 
|---|---|---|---|
| nestloop_only | no |
| hashjoin_only | no |
| mergejoin_only | yes |
| no_hashagg | no |
| no_sort_opt | no |
| index_scans | yes |
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
