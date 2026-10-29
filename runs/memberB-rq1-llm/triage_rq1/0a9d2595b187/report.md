# wrong_result: result differs under plan variant mergejoin_only: 1 rows by default, 1 rows with variant

* Oracle: **plan-variant**, signature `0a9d2595b187`
* Reproduced: 3/3 on 20devel
* Reduced: 1 -> 1 statements, 521 -> 43 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 0a9d2595b187: wrong_result via plan-variant
-- default plan:
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a2.c3)) - a2.c3)) FROM (t4 a1 JOIN t3 AS a2 ON (a1.c0 = a2.c0));
-- plan variant mergejoin_only (must return the same rows):
SET enable_nestloop = 'off';
SET enable_hashjoin = 'off';
SELECT MODE () WITHIN GROUP (ORDER BY ( (JUSTIFY_HOURS (a2.c3)) - a2.c3)) FROM (t4 a1 JOIN t3 AS a2 ON (a1.c0 = a2.c0));
RESET enable_nestloop;
RESET enable_hashjoin;
```

## Observed on the test server

`query`:

```
    00:00:00
```

## Where the bug is (localization)

**planner**: the answer depends on planner settings: mergejoin_only; the code paths these switch are the first suspects.

Settings and the code they switch:

* `enable_hashjoin`: executor/nodeHashjoin.c, optimizer/path/joinpath.c
* `enable_nestloop`: executor/nodeNestloop.c, optimizer/path/joinpath.c

| plan variant | answer changes | 
|---|---|---|---|
| nestloop_only | no |
| hashjoin_only | no |
| mergejoin_only | yes |
| no_hashagg | no |
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
