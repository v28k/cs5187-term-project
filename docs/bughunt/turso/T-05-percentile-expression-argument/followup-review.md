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

## Second review (PR head fcfc80b): shared fraction step, fraction validated like SQLite

Findings of the review bot: (1) `Percentile::step` was a copy of `fraction_step` that differed only in the upper bound
100; (2) the fraction was not checked like SQLite (`percentile_disc(1, 2)`, `percentile_disc(1, NULL)`,
`percentile(1, 'abc')` returned NULL instead of an error).

Change: one commit on top of fcfc80b, "core: share the percentile fraction check and validate it like SQLite"
(`followup-fraction.patch`, branch `percentile-fraction`, tree fa3178d97b0de693f35c667b16abcf2b37152a9e; author
Venu Kummari, committer v28k).
- `fraction_step(state, args, name, max_fraction)` is used by percentile (100.0), percentile_cont and
  percentile_disc (1.0), like `mxFrac` in SQLite's percentile.c. It follows SQLite's `percentStep` order: the fraction
  must be INTEGER, REAL or numeric TEXT in [0, max] ("the fraction argument to <name>() is not between 0.0 and
  1.0|100.0"), it must be the same on every row within 0.001 of the scaled fraction ("... is not the same for all input
  rows"), then a NULL value is skipped and TEXT/BLOB values fail ("input to <name>() is not numeric").
- One "first error" slot replaces the two error slots: SQLite stops at the first error, and `finalize` returns it
  before anything else, so the error also appears when no value was aggregated. Errors are formatted `String`s.
- `core/percentile.rs` vs fcfc80b: 76 insertions, 101 deletions (it shrinks by 25 lines).

Checked against SQLite 3.54.1: the five cases above raise SQLite's errors with the same wording; over an empty table
all five return NULL (SQLite never calls the step); a row with a NULL value and fraction 2 raises the fraction error;
`percentile_cont(a, a * 0.1)` raises the "not the same" error. These 8 cases were added to
`percentile-expression-argument.sqltest`; 7 fail without the change (the empty-table case passes either way).

Tests (8 Nov 2026): the two percentile sqltest files 23/23; full `sqlite-sqltests` corpus, cli backend: 12713 passed,
4 skipped, and `big-db` / `big-db-mvcc` failed only because the disk filled up during that run (re-run with free disk: both passed);
`cargo test -p turso_core --lib percentile` 3 passed; `cargo fmt --check` and
`cargo clippy --workspace --all-features --all-targets -- --deny=warnings` clean. JS backend not run locally.

## CI after the second follow-up (PR head 05d4506b)

The four SQL-test jobs failed on one existing test, `turso-sqltests/within-group.sqltest`
`percentile_disc_rejects_percentage`: it expected `percentile_disc(x, 100)` to return nothing, the old behaviour the
review asked to fix. SQLite 3.54.1 raises "the fraction argument to percentile_disc() is not between 0.0 and 1.0".
Local run of all `turso-sqltests` (cli backend): 3630 passed, 1 failed (that test). Fix: one commit on top of
05d4506b, "test: expect the fraction error for percentile_disc(x, 100)" (`followup-within-group-test.patch`, tree
bb12e6a2881e1b4b72c5adac9a9d27874ed1a5a6); `within-group.sqltest` then passes 75/75.
