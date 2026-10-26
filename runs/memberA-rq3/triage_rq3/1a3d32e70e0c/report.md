# wrong_result: result differs under plan variant xversion: 218 rows by default, 211 rows with variant

* Oracle: **cross-version**, signature `1a3d32e70e0c`
* Reproduced: 3/3 on 20devel
* Reduced: 4 -> 2 statements, 169 -> 13 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 1a3d32e70e0c: wrong_result via cross-version
INSERT INTO t2 AS a1 (c2, c3) SELECT LAG ('epoch'::timestamptz) IGNORE NULLS OVER (ORDER BY 2) AS c0, '{NULL}'::text[] AS c1 FROM v0 AS a2 ON CONFLICT DO NOTHING;
WITH rc AS (SELECT) SELECT FROM (SELECT FROM t2);
```

## Observed on the test server

`query`:

```
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    ... (49 rows)
```

## Where the bug is (localization)

**not_toggled_by_planner_settings**: no planner setting removes the disagreement: suspect an always-applied rewrite, constant folding, a planner support function, or expression evaluation.

| plan variant | answer changes | agrees with release |
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
