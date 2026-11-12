# Filing steps (D-01): issue first, then the fix PR

**Before anything: DuckDB's `AI_POLICY.md`.** It allows AI-assisted code, but requires that issues, PR descriptions
and replies to maintainers are written by you, in your own words, and that you can explain the change yourself;
autonomous-agent contributions are closed. So: read `report.md` and the diff in `fix.patch` until you can explain
them, and use `issue.md` / `pr.md` as notes to rewrite in your own words rather than pasting them. Reviewers will
ask questions; answer them yourself.

## 1. Re-check (5 min)

```bash
pip install --pre -U duckdb
```

```bash
python -c "import duckdb; db=duckdb.connect(); db.execute('CREATE TABLE a (x INTEGER); INSERT INTO a VALUES (1), (2)'); print(db.execute('SELECT min((SELECT [1])) FROM a').fetchall())"
```

If this prints `[([1],)]`, the bug was fixed meanwhile: do not file; tell me.
Then search https://github.com/duckdb/duckdb/issues?q=%22Cannot+copy+BoundSubqueryExpression%22 and
https://github.com/duckdb/duckdb/pulls?q=minmax+collation for anything new since 8 Nov 2026.

## 2. Open the issue

https://github.com/duckdb/duckdb/issues/new?template=bug_report.yml — fill the form from `issue.md`:
title; "What happens?"; "To Reproduce" (the SQL block); OS: Linux x86_64; DuckDB Version: as in `issue.md`;
Client: Python and CLI; Full Name: Venu Kummari; Affiliation: IIT Guwahati; latest build tested: main (see 3. below
if you want to name your own build's commit); tick the three checkboxes. Note the issue number.

## 3. Fork, apply the patch, build, test

```bash
gh repo fork duckdb/duckdb --clone=false
```

```bash
git clone https://github.com/<your-user>/duckdb && cd duckdb
```

```bash
git remote add upstream https://github.com/duckdb/duckdb && git fetch upstream main && git checkout -b fix-minmax-subquery-argument upstream/main
```

```bash
git am /path/to/D-01-minmax-nested-subquery/fix.patch
```

(If `git am` reports a conflict because `main` moved: `git am --abort`, then `git apply -3 fix.patch`, fix the
conflict in `src/function/aggregate/distributive/minmax.cpp`, `git add` and commit with the message from the patch.)

```bash
GEN=ninja make release
```

(about 2 hours on 4 cores the first time; `make reldebug` is what the project recommends for development.)

```bash
build/release/test/unittest test/sql/aggregate/aggregates/test_minmax_subquery_argument.test
```

```bash
build/release/test/unittest "test/sql/collate/*"
```

```bash
build/release/test/unittest "test/sql/subquery/*"
```

```bash
build/release/test/unittest
```

(the last one is the fast suite; it should pass apart from failures that also happen on unpatched `main`.)

```bash
python3 -m pip install clang-format==11.0.1 && make format-fix && git status
```

(no changes expected; if there are, amend the commit.)

## 4. Push, run CI on your fork, open the PR

DuckDB's CONTRIBUTING.md asks to run CI on your fork before opening the PR (Actions tab of your fork: enable
workflows, and push the tags once: `git fetch upstream --tags && git push origin --tags`).

```bash
git push -u origin fix-minmax-subquery-argument
```

Open the PR from `<your-user>:fix-minmax-subquery-argument` to `duckdb/duckdb:main` (not a draft). Title and body:
`pr.md`, with `#ISSUE` replaced by the issue number from step 2, rewritten in your own words.

## 5. Tell me

The issue and PR numbers; I record them in PROGRESS.md and `src/known_bugs/duckdb.yaml`.
