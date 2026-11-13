# DuckDB candidate ledger (precision ledger input; one line per signature)

| Signature | Oracle | Verdict | Notes |
|---|---|---|---|
| 2a6e4c3ebd4a | internal error | **real, D-01** | min/max over nested value with a subquery (2.0.0 regression) |
| 0184a1f8f3ea | internal error | **real, D-02** | outer-join/MERGE condition with two subqueries |
| 8a79e28804df | cross-version (nightly vs 2.0.0) | false positive (harness) | settings changed by an earlier test case (SET ...) leaked across ROLLBACK; fixed: driver resets session settings after every test case |
| 5e07637e93c5 | cross-version | false positive (generator) | POSITIONAL JOIN with a GROUP BY view: row order of the view is undefined; fixed: POSITIONAL JOIN only between base tables |
| 6ead81538cdc | metamorphic tlp_where | false positive (harness) | float masking decided per side: the TLP side with aggregates rounded 5e-324 to 0; fixed: one masking decision per check (as the PostgreSQL executor) |
