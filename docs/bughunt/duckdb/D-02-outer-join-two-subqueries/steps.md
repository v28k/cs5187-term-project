# Steps for the owner (D-02)

Nothing to do: the bug is fixed on DuckDB `main` by 57a6875edf (PR #28246, issue #28156, merged 2 Nov 2026), after
the nightly we found it on. Do not file. The next nightly wheel / 2.0.x release that contains 57a6875edf will not
reproduce it (`pip install --pre -U duckdb`, then run `repro.sql`).
