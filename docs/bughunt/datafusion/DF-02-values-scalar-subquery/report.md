# DF-02: scalar subquery inside VALUES: "Internal error: ScalarSubqueryExpr evaluated before the subquery was executed"

| | |
|---|---|
| Status | **candidate: re-run on `main` before filing** (reproduced on the latest release wheel only) |
| Target | Apache DataFusion |
| Kind | INTERNAL error on a valid query (DataFusion itself says "likely caused by a bug in DataFusion's code") |
| Affected | datafusion-python 55.0.0 (DataFusion 55, where physical scalar-subquery evaluation, `ScalarSubqueryExpr`, is new). `main` not tested (build not allowed in our environment); the error site still exists on main (`datafusion/physical-expr/src/scalar_subquery.rs:125`) |
| Found by | grammar fuzzer, DataFusion target, internal-error oracle (8 Nov 2026) |

## Reproducer

```sql
VALUES ((SELECT 1), 5);
```

Actual: `Internal error: ScalarSubqueryExpr evaluated before the subquery was executed. This issue was likely caused by
a bug in DataFusion's code.` Expected: `(1, 5)`.

## Likely cause

The VALUES rows are evaluated when the values plan is built (or before the `ScalarSubqueryExec` that fills the shared
results container has run), so the `ScalarSubqueryExpr` in the row finds no result yet. Not verified on main.

## Duplicate search (8 Nov 2026)

main up to 9d15cf0: related recent fixes #26836 (uncorrelated scalar subquery as a constant in ordering checks), #26723,
#26544; none about VALUES. No `.slt` test with a scalar subquery in a VALUES row. Owner: search
https://github.com/apache/datafusion/issues?q=%22ScalarSubqueryExpr+evaluated+before%22 before filing.
