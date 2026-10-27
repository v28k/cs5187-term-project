# wrong_result: metamorphic check expr:llm_nullif_null_reduction failed: 46 rows vs 46 rows

* Oracle: **metamorphic:expr**, signature `a819a7520c99`
* Reproduced: 3/3 on 20devel
* Reduced: 4 -> 1 statements, 69 -> 12 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of a819a7520c99: wrong_result via metamorphic:expr
-- the two queries below must return the same rows (as a multiset):
SELECT UPPER (LEFT ('é'::text, 3));
SELECT UPPER ((NULLIF( (LEFT ('é'::text, 3)) , NULL::text COLLATE "POSIX")));
```

## Observed on the test server

`lhs`:

```
    É
```

`rhs`:

```
    é
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
