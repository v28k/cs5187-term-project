# T-05 follow-up: review finding on tursodatabase/turso#11595 (non-numeric input)

## Finding (review bot on the PR)

SQLite's percentile aggregates reject non-numeric input; Turso did not:

| Query | SQLite 3.54.1 | Turso before | Turso with the follow-up |
|---|---|---|---|
| `SELECT percentile_disc('5', 1)` | error `input to percentile_disc() is not numeric` | 5.0 | same error |
| `SELECT median('7')` | error `input to median() is not numeric` | 7.0 | same error |
| `SELECT percentile_cont('abc', 0.5)` | error `input to percentile_cont() is not numeric` | NULL | same error |
| `SELECT percentile(x'35', 50)` | error `input to percentile() is not numeric` | 5.0 | same error |
| `SELECT percentile_disc(NULL, 1) IS NULL` | 1 | 1 | 1 |

Reference: SQLite `ext/misc/percentile.c` (a non-NULL value whose type is TEXT or BLOB is an error). All SQLite
results above were checked with SQLite 3.54.1 (APSW). Turso prints the error as
`Extension error: input to ...() is not numeric`.

## Change (`followup-nonnumeric.patch`, branch `percentile-nonnumeric` of v28k/turso)

One commit, f4e3901e, on top of the PR head 79d092a, "core: reject non-numeric input to percentile aggregates",
author and committer Venu Kummari. Only `core/percentile.rs` and the PR's sqltest file change.

- `numeric_input(value, error)`: `None` for NULL, `Err(error)` for TEXT or BLOB, the number otherwise.
- `median`, `percentile`, `percentile_cont` and `percentile_disc` keep the first such error in a separate slot of
  their state (`step` cannot return an error) and `finalize` returns it before anything else, so the error also
  appears when no numeric row was aggregated. `percentile_cont` and `percentile_disc` share one step
  (`fraction_step`) that takes the function's own error message, so `percentile_disc` names itself.
- The separate slot keeps the existing handling of an out-of-range fraction unchanged (that is open issue #10413 /
  PR #10435, not part of this PR).

## Tests (8 Nov 2026, `tursodb` debug build of f4e3901e)

- `percentile-expression-argument.sqltest`, 5 new tests (the 4 errors and the NULL case; `\(\)` escaped because
  error expectations are regular expressions): all 10 tests in the file pass, plus `percentile-fraction.sqltest`.
  Without the code change the 4 error tests fail (the NULL case passes either way).
- Full `sqlite-sqltests` corpus, cli backend: 12707 passed, 4 skipped, 0 failed (487 s).
- `cargo fmt --check`: clean. `cargo clippy --workspace --all-features --all-targets -- --deny=warnings`: clean.
- JS backend: not run locally (the new tests print no floats, so no `@js` variant is needed; CI runs it).

## Handover

The push of branch `percentile-nonnumeric` to v28k/turso was refused from this environment (no write access), so
the commit is kept here as `followup-nonnumeric.patch`; applying it with `git am` onto 79d092a gives tree `c5d856b2d13931a027ef6cfa8135e2ab1467f1b1`. The PR branch is updated by a normal
(non-force) push of that branch onto `fix-percentile-expression-argument`; the step is done by the owner's release tool from the prompt given to the owner.
