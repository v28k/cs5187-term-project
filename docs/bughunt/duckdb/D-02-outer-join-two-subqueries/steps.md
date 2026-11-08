# Steps for the owner (D-02)

1. `pip install --pre -U duckdb`, run the three statements of `repro.sql`; they should still fail with
   "INTERNAL Error: Failed to bind column reference". If not, it was fixed meanwhile: do not file.
2. Search https://github.com/duckdb/duckdb/issues?q=%22Failed+to+bind+column+reference%22 for a new duplicate.
3. File https://github.com/duckdb/duckdb/issues/new?template=bug_report.yml with `issue.md`.
4. Tell me the issue number. `outer_join_two_subqueries.test` is ready for a fix PR if a maintainer asks.
