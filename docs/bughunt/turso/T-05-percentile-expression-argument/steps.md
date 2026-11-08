# Steps for the owner (T-05): issue first, then the fix PR

Turso's CONTRIBUTING.md ("Developing with AI coding agents") expects you to understand the code you submit and to
describe the change in your own words; its PR template has a required "Description of AI Usage" section, left for you
to fill in `pr.md`. Read `report.md` and the diff in `fix.patch` first.

## 1. Re-check and search (5 min)

Search https://github.com/tursodatabase/turso/issues?q=percentile and
https://github.com/tursodatabase/turso/pulls?q=percentile for anything new since 8 Nov 2026.

## 2. Fork, apply, build, test

```bash
gh repo fork tursodatabase/turso --clone=false
```

```bash
git clone https://github.com/<your-user>/turso && cd turso
```

```bash
git remote add upstream https://github.com/tursodatabase/turso && git fetch upstream main && git checkout -b fix-percentile-expression-argument upstream/main
```

```bash
git am /path/to/T-05-percentile-expression-argument/fix.patch
```

```bash
cargo build --bin tursodb
```

```bash
printf "CREATE TABLE t (a INTEGER, b TEXT);\nINSERT INTO t VALUES (1, 'x'), (2, 'y');\nSELECT percentile_disc(a + 0, 1) FROM t;\nSELECT percentile_disc(length(b), 1) FROM t;\n" | ./target/debug/tursodb -q -m list /tmp/t05.db
```

(expect `2.0` and `1.0`)

```bash
make -C sqlite/conformance run-one FILE=sqlite-sqltests/agg-functions/percentile-expression-argument.sqltest
```

```bash
cargo fmt --check && cargo clippy --workspace --all-features --all-targets -- --deny=warnings
```

```bash
make -C sqlite/conformance run-rust ARGS='--snapshot-filter __never__'
```

## 3. Open the issue, then the PR

1. https://github.com/tursodatabase/turso/issues/new — title and body from `issue.md` (in your own words). Note the
   number.
2. `git push -u origin fix-percentile-expression-argument`, open the PR against `tursodatabase/turso:main`, tick
   "allow edits from maintainers". Title and body from `pr.md`; replace `#ISSUE`; fill "Description of AI Usage".

## 4. Tell me the issue and PR numbers.
