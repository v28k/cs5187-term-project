# E-01: corr() / regr_r2() / regr_slope() of a constant input differ between serial and partial aggregation

Status: **reproduced, root-caused, patch written and checked on the reproducer. Regression
test and `make check` still to do. Duplicate search: none found on pgsql-bugs (2 Nov 2026).
NOT YET FILED.**
Found by our fuzzer (plan-variant oracle, campaign candidate `c5a5ed497011`).

## Summary

For a constant input, `corr()`, `regr_r2()` and `regr_slope()` return NULL with serial
aggregation but 1 with partial aggregation (partitionwise aggregate or parallel query).
Since commit 64982876 ("Handle constant inputs to corr() and related aggregates more
precisely"), `float8_regr_accum()` keeps Sxx, Syy and Sxy exactly zero while all inputs
are equal, so the final functions return NULL. `float8_regr_combine()` still adds the
correction term `N1*N2*(Sx1/N1 - Sx2/N2)^2/N`, which is not exactly zero because of roundoff
in Sx1/N1 and Sx2/N2, so the combined state has Sxx > 0 and the result becomes 1.

## Reproducer

`E-01-corr-partial-aggregate.sql` (self-contained).

| Build | serial | partitionwise | parallel (4 workers) |
|---|---|---|---|
| 18.6 | 1 | 1 | 1 (consistent, old semantics) |
| master 26bd08fb, 126976a8, 633dee1b | NULL | **1** | **1** |
| 633dee1b + patch | NULL | NULL | NULL |

Non-constant inputs give identical results with and without the patch.

## Fix

`E-01-corr-partial-aggregate.patch`: in `float8_regr_combine()`, compute the common values
Cx/Cy first and add the correction terms only for a variable that is not constant
(Cx / Cy is NaN), exactly as `float8_regr_accum()` does.

## To do before filing

1. Add a regression test to `src/test/regress/sql/aggregates.sql` (partitionwise
   aggregate over a constant column) and update the expected output.
2. Run `make check` on the patched tree (`/root/pgfuzz/src/corrfix-wt`, install
   `/root/pgfuzz/install/corrfix`).
3. File at https://www.postgresql.org/account/submitbug/ (version: master / 19).
