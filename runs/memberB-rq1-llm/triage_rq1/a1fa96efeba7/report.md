# wrong_result: result differs under plan variant no_join_reorder: 1 rows by default, 1 rows with variant

* Oracle: **plan-variant**, signature `a1fa96efeba7`
* Reproduced: 3/3 on 20devel
* Reduced: 1 -> 1 statements, 537 -> 56 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of a1fa96efeba7: wrong_result via plan-variant
-- default plan:
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a3.c3)) - a3.c3 * 1)) c1 FROM (v0 AS a1 FULL JOIN tp AS a2 ON TRUE JOIN t3 AS a3 ON (a1.c0 = a3.c0)) WHERE TRUE;
-- plan variant no_join_reorder (must return the same rows):
SET join_collapse_limit = '1';
SET from_collapse_limit = '1';
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a3.c3)) - a3.c3 * 1)) c1 FROM (v0 AS a1 FULL JOIN tp AS a2 ON TRUE JOIN t3 AS a3 ON (a1.c0 = a3.c0)) WHERE TRUE;
RESET join_collapse_limit;
RESET from_collapse_limit;
```

## Observed on the test server

`query`:

```
    00:00:00
```

## Where the bug is (localization)

**planner**: the answer depends on planner settings: nestloop_only, mergejoin_only, index_scans, no_join_reorder; the code paths these switch are the first suspects.

Settings and the code they switch:

* `enable_bitmapscan`: executor/nodeBitmapHeapscan.c, optimizer/path/indxpath.c
* `enable_hashjoin`: executor/nodeHashjoin.c, optimizer/path/joinpath.c
* `enable_mergejoin`: executor/nodeMergejoin.c, optimizer/path/joinpath.c
* `enable_nestloop`: executor/nodeNestloop.c, optimizer/path/joinpath.c
* `enable_seqscan`: optimizer/path/indxpath.c, executor/nodeIndexscan.c
* `join_collapse_limit`: optimizer/plan/initsplan.c (join reordering)

| plan variant | answer changes | 
|---|---|---|---|
| nestloop_only | yes |
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
| no_join_reorder | yes |
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
