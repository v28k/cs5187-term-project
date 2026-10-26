# wrong_result: result differs under plan variant no_self_join_elim: 101 rows by default, 101 rows with variant

* Oracle: **plan-variant**, signature `8a0e13634ebf`
* Reproduced: 3/3 on 20devel
* Reduced: 3 -> 1 statements, 235 -> 50 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 8a0e13634ebf: wrong_result via plan-variant
-- default plan:
SELECT CASE a2.c2 WHEN a1.c2 THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb WHEN a2.c2 THEN a1.c2 ELSE a2.c2 END FROM (t1 a1 JOIN t1 a2 USING (c0)) GROUP BY ROLLUP (a1.c2, a2.c2);
-- plan variant no_self_join_elim (must return the same rows):
SET enable_self_join_elimination = 'off';
SELECT CASE a2.c2 WHEN a1.c2 THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb WHEN a2.c2 THEN a1.c2 ELSE a2.c2 END FROM (t1 a1 JOIN t1 a2 USING (c0)) GROUP BY ROLLUP (a1.c2, a2.c2);
RESET enable_self_join_elimination;
```

## Observed on the test server

`query`:

```
    NULL
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    {"a": [3, 4, 5], "k": 0}
    ... (101 rows)
```

## Where the bug is (localization)

**planner**: the answer depends on planner settings: no_self_join_elim; the code paths these switch are the first suspects.

Settings and the code they switch:

* `enable_self_join_elimination`: optimizer/plan/analyzejoins.c (self-join elimination)

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
| parallel | no |
| partitionwise | no |
| no_partition_pruning | no |
| geqo | no |
| no_join_reorder | no |
| tiny_work_mem | no |
| no_reordering | no |
| no_self_join_elim | yes |
| no_eager_agg | no |
| jit | no |

## Before filing

1. Decide which side is right (SQL standard / documentation) and say why.
2. Search pgsql-bugs and pgsql-hackers for the message / function names.
3. Check the newest master and the latest release; bisect with scripts/bisect_pg.sh.
4. Record the verdict in triage/verdicts.yaml (it feeds the precision table).
