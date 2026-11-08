# Steps for the owner (DF-01): issue first, then the fix PR

DataFusion's AI policy (`docs/source/contributor-guide/ai-policy.md`) welcomes AI-assisted PRs only when the author
has read the whole PR, understands it end-to-end and answers reviewers in their own words; first-time contributors
are limited to 3 open PRs and AGENTS.md asks not to open several PRs at once on a first contribution. Suggestion:
open DF-01 first and DF-02 after DF-01 got a review. Read `report.md` and the diff in `fix.patch` first.

## 1. Re-check and search (5 min)

Search https://github.com/apache/datafusion/issues?q=__common_expr+update and
https://github.com/apache/datafusion/pulls?q=extract_update_assignments for anything new since 8 Nov 2026.

## 2. Open the issue

https://github.com/apache/datafusion/issues/new?template=bug_report.yml — fields from `issue.md` (Describe the bug,
To Reproduce, Expected behavior, Additional context, Willingness: "I plan to contribute a fix for this bug
independently"). Note the number.

## 3. Fork, apply, test

Enable GitHub Actions on your fork before pushing (the PR template asks for it).

```bash
gh repo fork apache/datafusion --clone=false
```

```bash
git clone https://github.com/<your-user>/datafusion && cd datafusion && git submodule update --init --depth 1 testing parquet-testing
```

```bash
git remote add upstream https://github.com/apache/datafusion && git fetch upstream main && git checkout -b fix-dml-common-subexpressions upstream/main
```

```bash
git am /path/to/DF-01-update-coalesce-common-expr/fix.patch
```

```bash
cargo test --profile ci -p datafusion-sqllogictest --test sqllogictests -- dml_update dml_delete update.slt delete.slt
```

```bash
cargo fmt --all && cargo clippy --all-targets --all-features -- -D warnings
```

```bash
cargo test --profile ci -p datafusion-sqllogictest --test sqllogictests
```

(the full sqllogictest run; ~15 min on 4 cores.)

## 4. Open the PR

```bash
git push -u origin fix-dml-common-subexpressions
```

PR against `apache/datafusion:main`, title and body from `pr.md` (replace `#ISSUE`, in your own words).

## 5. Tell me the issue and PR numbers.
