# BUG #19826: reply to Tom Lane's v3 (12 Nov 2026)

Thread: <https://postgr.es/m/19826-4b769cb5342fdfe7@postgresql.org>

## What Tom's v3 changes and whether it is right

Checked on PostgreSQL master `b0496e3` with assertions enabled. v3 applies cleanly and
`make check` passes 243 of 243 tests.

| v3 change | Check | Verdict |
|---|---|---|
| Overflow block copied from `float8_regr_accum()`; `Sx1`/`Sx2` take the place of `transvalues[1]`/`newvalX` | an error is raised only when finite sums give an infinite result, as in accum | correct |
| `float8_pl(Sx1, Sx2)` becomes plain `Sx1 + Sx2` | an Sx/Sy overflow from finite sums is still caught by the new block | correct, nothing lost |
| The Inf/NaN test for forcing `Sxy` looks at the sums `Sx`/`Sy`, not at a single new value | one Inf or NaN anywhere in a state makes that state's sum Inf or NaN | correct |
| `float8_eq(Cx1, Cx2)`: NaN = NaN counts as equal | two states that both saw distinct values keep `Cx = NaN`, so the correction is applied | correct |
| The final `isinf → NaN` lines (Tom thinks they are dead code) | accum never leaves an infinite Sxx/Syy/Sxy in a state, so they only matter for hand-made arrays | agree; keep them |

**Tom's "made-up data" remark is only half right.** The first six numbers in both states are the
real transition states of the `regr_test` rows with `x IN (10,20,30)` and `x IN (80,100)`: the
queries just above that test print exactly those numbers. Only the last two entries (`7,8` and
`7,9`, the common-value slots added by 649828769) don't match those rows. Set them to
`NaN,NaN`, and the test:

* reaches the path where both correction terms are applied, which the new `regr_part` test never
  reaches because its X is constant;
* gives `{5,240,6280,1490,95080,8680,NaN,NaN}`, the sums over the whole table, as before 649828769.

v4 = v3 + that fix + two overflow cases + one "Inf input is not an overflow" case. Tested:
`make check` 243/243 on master `b0496e3` with assertions. The new direct tests give the same
output with and without the `float.c` change, so they add coverage and do not test the fix itself.

## What to do

1. Reply to Tom's mail with **Reply All**, so that Tom and `pgsql-bugs` both get it and it stays
   in the same thread. Send from `venu2805k@gmail.com`, as in the thread.
2. Send it as **plain text** (Gmail: three dots, then "Plain text mode"). Write below the quoted
   lines and delete the rest of the quoted mail.
3. Attach **only** `v4-0001-Make-float8_regr_combine-handle-edge-cases-like-f.patch` from this folder.
4. Paste the text below. Leave the git author of v4 as Tom: v3 is his, and the `Author:` line in
   the commit message already names you.
5. Then wait. If Tom pushes it, the commit appears on master and is back-patched to 19; record
   the commit hash in `README.md` and in the paper's bug table.

## Mail text (paste as is)

```
On Thu, Nov 12, 2026 at 1:53 AM Tom Lane <tgl@sss.pgh.pa.us> wrote:
> I studied this a bit, and remained unhappy about one point: it's
> not clear that float8_regr_combine() has the same behavior for
> overflow cases as float8_regr_accum().  Maybe it does, but I don't
> think readers should have to spend time convincing themselves of that.
> I suggest adjusting it to use the same block of overflow-handling
> logic that float8_regr_accum() has, as in v3 attached.  Does that
> seem sane to you?

Yes.  I compared it with float8_regr_accum() case by case: Sx1 and
Sx2 play the roles of transvalues[1] and newvalX there, so we still
only raise an error when finite sums give an infinite result, and
dropping float8_pl() for Sx and Sy loses nothing because the new block
catches that overflow.  Testing Sx/Sy for the Inf/NaN case is right
too, since one Inf or NaN anywhere in a state makes its sum Inf or NaN.

> I suspect that the last few lines in my v3, [...] are dead code for
> the same reason, but again that doesn't seem like something to
> depend on

Agreed.  A state built by float8_regr_accum() never has an infinite
Sxx, Syy or Sxy, so those lines only matter for hand-made states, but
they keep the two functions in step.

> Yeah, it seems clear that that test case is just made-up data,
> probably put there just so that float8_regr_combine() shows as having
> some coverage in our coverage tests.  I wonder whether the new test
> doesn't render it useless even for that.  It might be better to change
> it to exercise something your new test still doesn't reach, like an
> overflow error.

The first six entries aren't made up: they are the transition states
for the regr_test rows with x IN (10,20,30) and x IN (80,100), which
the queries just above print.  Only the commonX/commonY entries (7,8
and 7,9) don't fit those rows, which have distinct X and Y values.
With NaN in both, the test goes through the path where both
correction terms are applied, which regr_part doesn't reach since its
X is constant, and the result is again
{5,240,6280,1490,95080,8680,NaN,NaN}, the sums over the whole table.

I also added two overflow cases (Sx itself, and the Sxx correction
term alone) and one showing that an infinite input is not reported
as an overflow.  These give the same output with and without the
float.c change, so they are coverage for the combine function rather
than a test of this fix.

v4 attached: your v3 plus those test changes and a paragraph about
them in the commit message.  make check passes on master (b0496e3)
with assertions enabled.

Regards,
Venu
```
