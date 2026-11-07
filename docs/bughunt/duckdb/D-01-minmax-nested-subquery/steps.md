# Steps for the owner (D-01)

1. Re-run `repro.sql` on the newest nightly: `pip install --pre -U duckdb` then
   `python -c "import duckdb; db=duckdb.connect(); [print(db.execute(s).fetchall()) for s in open('repro.sql').read().split(';') if s.strip() and not s.strip().startswith('--')]"`
   (the SELECTs should still fail; if they pass, the bug was fixed meanwhile: do not file).
2. Search https://github.com/duckdb/duckdb/issues?q=%22Cannot+copy+BoundSubqueryExpression%22 for a new duplicate.
3. File https://github.com/duckdb/duckdb/issues/new?template=bug_report.yml with the text of `issue.md`
   (fill the form fields with the values given there).
4. Tell me the issue number; I record it in PROGRESS.md and `src/known_bugs/duckdb.yaml`.
5. A fix PR is optional: `minmax_subquery_argument.test` is ready for `test/sql/aggregate/aggregates/`; the fix
   itself is a design choice for the maintainers (see report.md "Possible fixes").
