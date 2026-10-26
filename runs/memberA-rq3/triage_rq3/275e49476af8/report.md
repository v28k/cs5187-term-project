# wrong_result: result differs under plan variant mergejoin_only: 146 rows by default, 146 rows with variant

* Oracle: **plan-variant**, signature `275e49476af8`
* Reproduced: 3/3 on 20devel
* Reduced: 5 -> 2 statements, 15 -> 5 tokens
* Verdict: TODO: real | duplicate | false_positive | not_a_bug | flaky

## Reproducer

```sql
-- pgfuzz triage of 275e49476af8: wrong_result via plan-variant
CREATE VIEW n1 AS SELECT LAG (a1.c0) OVER (ORDER BY a2.c4) AS c0, a2.c5 AS c1, '[1,10)'::text AS c2 FROM (ti AS a1 FULL JOIN t3 AS a2 ON (a1.c1 = a2.c5));
-- default plan:
SELECT a1 FROM n1 a1;
-- plan variant mergejoin_only (must return the same rows):
SET enable_nestloop = 'off';
SET enable_hashjoin = 'off';
SELECT a1 FROM n1 a1;
RESET enable_nestloop;
RESET enable_hashjoin;
```

## Observed on the test server

`query`:

```
    (,B,"[1,10)")
    (,C,"[1,10)")
    (,D,"[1,10)")
    (,E,"[1,10)")
    (,F,"[1,10)")
    (,G,"[1,10)")
    (,H,"[1,10)")
    (,I,"[1,10)")
    (,J,"[1,10)")
    (,K,"[1,10)")
    (,L,"[1,10)")
    (,M,"[1,10)")
    (,N,"[1,10)")
    (,O,"[1,10)")
    (,P,"[1,10)")
    (,Q,"[1,10)")
    (,R,"[1,10)")
    (,S,"[1,10)")
    (,T,"[1,10)")
    (,U,"[1,10)")
    (,V,"[1,10)")
    (,W,"[1,10)")
    (,X,"[1,10)")
    (,Y,"[1,10)")
    (,Z,"[1,10)")
    (,A,"[1,10)")
    (,B,"[1,10)")
    (,C,"[1,10)")
    (,D,"[1,10)")
    (,E,"[1,10)")
    ... (146 rows)
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
