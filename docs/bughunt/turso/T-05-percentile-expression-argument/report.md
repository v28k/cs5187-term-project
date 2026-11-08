# T-05: percentile_disc / percentile_cont with an expression as the value argument

| | |
|---|---|
| Status | **candidate: re-run on Turso `main` before filing** (reproduced on pyturso 0.8.3 only; building/running main is blocked here) |
| Target | Turso (https://github.com/tursodatabase/turso) |
| Kind | wrong result (NULL instead of a value) and a bogus error; differential oracle Turso vs SQLite 3.54.1 |
| Found by | Turso campaign (8 Nov 2026), cross-engine differential; cluster of candidates reduced to `SELECT PERCENTILE_DISC(ABS(''), 1)` etc. |

See `issue.md` for the reproducer and expected results (from SQLite 3.54.1). Recent related work on main:
0c00e0f02 "core: reject a rowid in the fraction of percentile_disc and percentile_cont" (the area is active; the owner
should check whether main still fails). Duplicate search: https://github.com/tursodatabase/turso/issues?q=percentile
