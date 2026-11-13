# E-01: corr() / regr_r2() / regr_slope() of a constant input differ between serial and partial aggregation

Status: **FIXED upstream with our patch: ef1b740441 "Make float8_regr_combine() handle edge cases like float8_regr_accum()" (Tom Lane, 12 Nov 2026, Author: Venu Kummari, back-patched to 19).** Earlier: **reproduced (base 26bd08fb, 126976a8, newest master 633dee1b), root-caused,
patch with regression test, `make check` 239/239 on 633dee1b + patch. Duplicate search:
none found on pgsql-bugs or in master's git log (2 Nov 2026). FILED as BUG #19826 (2 Nov 2026), patch sent as a reply.**
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

`v1-0001-Keep-constant-input-sums-exact-in-float8_regr_combine.patch` (against master 633dee1b):

- `float8_regr_combine()`: compute the common values Cx/Cy first and add the
  correction terms only for a variable that is not constant (Cx or Cy is NaN), exactly
  as `float8_regr_accum()` does since 64982876;
- regression test in `aggregates.sql`: partitionwise aggregate over a constant column,
  with the plan shown so the combine path is exercised;
- one existing expected output changes: the direct call
  `float8_regr_combine('{3,60,200,750,20000,2000,7,8}', '{2,180,200,740,57800,-3400,7,9}')`
  combines two hand-made states whose common X value (7) contradicts their means
  (20 and 90). Real input cannot produce such states; with the patch the combine trusts
  the common value, so Sxx is 400 instead of 6280. If preferred, the test input can be
  changed to consistent states instead.

Non-constant inputs give identical results with and without the patch (checked with
partitionwise aggregation over 300 varying rows).

## Severity

Silent, plan-dependent wrong result (no crash, no data corruption), limited to
zero-variance input and to plans with partial aggregation. A regression in master since
64982876 (PostgreSQL 19 development cycle; not verified on a 19 build); 18.6 is
consistent.

## How we found it

Our fuzzer's plan-variant oracle ran the generated query `SELECT corr(1.0/3, 1.0/3) FROM tl`
(tl: a list-partitioned table) with and without `enable_partitionwise_aggregate` and saw
NULL against 1 (campaign candidate `c5a5ed497011`). Triage reduced it to one statement;
we then confirmed the parallel-query variant by hand.

## Draft for https://www.postgresql.org/account/submitbug/

- PostgreSQL version: master (20devel), 633dee1b
- Operating system: Linux x86_64
- Short description: corr()/regr_r2()/regr_slope() of constant input: NULL serially, 1 with partial aggregation

```
Since commit 64982876 ("Handle constant inputs to corr() and related
aggregates more precisely"), corr(), regr_r2() and regr_slope() return NULL
for a constant input. They still return 1 when the aggregate is computed in
parallel or with partitionwise aggregation:

CREATE TABLE e01 (k int, x float8) PARTITION BY LIST (k);
CREATE TABLE e01_1 PARTITION OF e01 FOR VALUES IN (1);
CREATE TABLE e01_2 PARTITION OF e01 FOR VALUES IN (2);
CREATE TABLE e01_3 PARTITION OF e01 FOR VALUES IN (3);
INSERT INTO e01 SELECT 1 + g % 3, 1.0 / 3 FROM generate_series(1, 80) g;
ANALYZE e01;
SELECT corr(x, x), regr_r2(x, x), regr_slope(x, x) FROM e01;
  -- NULL | NULL | NULL
SET enable_partitionwise_aggregate = on;
SELECT corr(x, x), regr_r2(x, x), regr_slope(x, x) FROM e01;
  -- 1 | 1 | 1

The same happens with a parallel Gather over Partial Aggregate (300000
constant rows, 4 workers). Reproduced on master 633dee1b; 18.6 returns 1 in
both cases (old behaviour).

Cause: float8_regr_accum() deliberately keeps Sxx, Syy and Sxy exactly zero
while all inputs are equal, but float8_regr_combine() still adds
N1*N2*(Sx1/N1 - Sx2/N2)^2/N, which is not exactly zero because of roundoff,
so the combined state has Sxx > 0.

A patch that applies the same rule in float8_regr_combine() (add the
correction only when Cx/Cy is NaN), with a regression test, follows as a
reply. make check passes. One existing expected output changes: a direct
float8_regr_combine() call combines two hand-made states whose common X
value (7) contradicts their sums.

Found with a grammar-based fuzzer that compares query results across
planner settings.
```

## Review round 1 (Tom Lane, 3 Nov 2026) and v2

Tom Lane's points: (1) the combine function also lacks the logic added to float8_regr_accum()
by 7774249d0 (#19615) that forces Sxy to NaN when one input is constant and the other is
Inf/NaN; (2) the v1 comments did not answer the questions a reader has.

v2 (`v2-0001-Make-float8_regr_combine-handle-constant-inputs-l.patch`, against master 633dee1b):
- adds the correction terms only for a variable whose common value is unknown (unchanged idea);
- when the Sxy correction is skipped because one variable is constant, forces Sxy to NaN if
  Sx or Sy is Inf/NaN (the inputs are not visible in the combine function, but a sum that
  includes an Inf or NaN is itself Inf or NaN);
- rewritten comment explaining why the term can be dropped (both means are exactly c in exact
  arithmetic, Sx1/Sx2 are rounded sums) and why the NaN case must be handled;
- new commit message referencing 649828769 and 7774249d0; regression test now checks constant
  input and Inf/NaN in one partition with partitionwise aggregation against the serial plan;
- make check 239/239.

Note for the reply: with states built by float8_regr_accum, a partial state that saw an Inf or
NaN already has Sxy = NaN, so the explicit forcing does not change the results of the tests;
it keeps the combine function correct on its own instead of relying on that.

### Reply to send (reply-all to Tom's message, plain text, attach the v2 patch)

```
On Mon, Nov 3, 2026, Tom Lane wrote:
> isn't it also missing the latter routine's recently-added logic for
> forcing outputs to NaN when necessary?

Yes, thanks. When I skip the Sxy correction because one variable is
constant, the NaN that 0 * Inf would have produced is lost. v2 forces Sxy
to NaN in that case, as float8_regr_accum does since 7774249d0. The
combine function can't see the inputs, so it tests Sx and Sy instead: a
sum that includes an Inf or NaN is Inf or NaN.

As far as I can tell, a partial state that has seen an Inf or NaN already
carries Sxy = NaN from float8_regr_accum, so this doesn't change any
result I could produce through SQL, but the combine function shouldn't
depend on that.

> the proposed comments read like AI slop

Fair. I rewrote the comment to say why the term can be dropped: if both
states saw only the value c, both means are c exactly and Sxx1/Sxx2 are
zero, but Sx1 and Sx2 are rounded sums, so the computed difference of the
means is a small nonzero number that leaves Sxx positive, and corr() of a
constant input becomes 1 under partial aggregation. The commit message
now explains the history (649828769, 7774249d0).

The regression test now compares partitionwise aggregation with the
serial plan for a constant input and for an Inf or NaN in one partition
with the other input constant. One existing expected output changes: the
direct float8_regr_combine() call whose two states have the same common X
value (7) but different sums gives Sxx 400 instead of 6280. Those states
can't arise from real input; I can change that test's input instead if
you prefer.

make check passes on master (633dee1b).

v2 attached.

Regards,
Venu
```
