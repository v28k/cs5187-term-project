# Filing steps (DF-02): issue first, then the fix PR

Same policy notes as DF-01 (DataFusion AI policy; at most 3 open PRs; better one PR at a time on a first
contribution, so open this one after DF-01 has had a review). Read `report.md` and `fix.patch` first.

## 1. Re-check and search

https://github.com/apache/datafusion/issues?q=%22ScalarSubqueryExpr+evaluated+before%22 and
https://github.com/apache/datafusion/issues?q=VALUES+scalar+subquery for anything new since 8 Nov 2026.

## 2. Open the issue

https://github.com/apache/datafusion/issues/new?template=bug_report.yml — fields from `issue.md`. Note the number.

## 3. Fork (once), apply, test

```bash
cd datafusion && git fetch upstream main && git checkout -b fix-values-scalar-subquery upstream/main
```

```bash
git am /path/to/DF-02-values-scalar-subquery/fix.patch
```

```bash
cargo test --profile ci -p datafusion-sqllogictest --test sqllogictests -- subquery values insert explain
```

```bash
cargo fmt --all && cargo clippy --all-targets --all-features -- -D warnings
```

```bash
cargo test --profile ci -p datafusion-sqllogictest --test sqllogictests
```

## 4. Open the PR

```bash
git push -u origin fix-values-scalar-subquery
```

PR against `apache/datafusion:main`, title and body from `pr.md` (replace `#ISSUE`, in your own words).

## 5. Tell me the issue and PR numbers.
