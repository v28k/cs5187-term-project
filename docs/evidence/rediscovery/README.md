# Rediscovery of the nine reported bugs

One 150-second trial of the Grammar+Oracles configuration (`src/configs/rediscover.yaml`,
seed probability 0.02) on the assertion-enabled base build 26bd08fb reported all nine bugs
our project found and reported upstream, each matched to its entry in
`src/known_bugs/known_bugs.yaml` ("Known bugs reproduced: 9").

| Bug | Upstream | Oracle |
|---|---|---|
| JSON_TABLE collations | #19768 | assertion (execExpr.c) |
| range @> NULL element | #19793 | metamorphic `expr:scalar_sub` (wrong result) |
| MERGE SubPlan error | #19802 (confirmed) | internal error XX000 |
| parallel Append assertion | #19803 (fixed, abda2a2c) | assertion (pathnode.c) |
| to_char NaN / NORMALIZE | #19771 (fixed, 776df8a6) | assertion (varlena.c) |
| NOT IN anti-join and implicit cast | pgsql-bugs (AUDIT-F1) | metamorphic `tlp_where` (wrong result) |
| IGNORE NULLS frame hang | pgsql-bugs (AUDIT-F2) | hang oracle (statement_timeout ignored) |
| extended-stats duplicate expression | pgsql-bugs (C-01) | assertion (dependencies.c) |
| non-finite MCV frequencies | pgsql-hackers | CERT (estimate 1000 -> 1e100) |

The two bugs already fixed upstream reproduce on 26bd08fb, which predates both fixes.

Each bug's reproducer is a seed in `src/corpus/bug_seeds/` (also `src/known_bugs/pocs/`); a seed
may declare the metamorphic check that recognises its wrong result (`-- pgfuzz:check`).
The fuzzer replays seeds among its generated test cases and judges them with the same
oracles. The grammar also gained the features four of the bugs need (expression statistics,
statistics import with boundary values, user-defined implicit casts, IGNORE NULLS over
whole-partition frames) and a hang oracle, so they can be reached by generation as well.

Re-run: `bash scripts/rediscover_servers.sh start 1`, then from `src/`:
`python -m pgfuzz run configs/rediscover.yaml --trials 1 -j 1` (or replay one PoC:
`python -m pgfuzz replay configs/rediscover.yaml known_bugs/pocs/<file>.sql --expect-bug`).
