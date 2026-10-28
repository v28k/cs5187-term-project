# Two likely-new bugs from the B3 (RQ1) campaign

Checked 28 Oct 2026. Neither appears in `known_bugs/`, `triage/verdicts.yaml`,
`docs/bughunt/`, `bugprogress/`, the pgsql-bugs / pgsql-hackers archives (web
search) or the upstream commit log, and both still fail on **today's upstream
master `4848fd675`** (built with `--enable-cassert`). Status: **new; N1 filed as BUG #19802 (28 Oct 2026), N2 being filed**. A search cannot rule out a report sent in the last few
days or a private patch, so check the pgsql-bugs list once more before filing.

| | N1: MERGE `SubPlan found with no parent plan` | N2: Parallel Append assertion |
|---|---|---|
| upstream report | **BUG #19802** (filed 28 Oct 2026 by Gowtham) | not filed yet |
| fuzzer signature | `3dc78dd95f41` (internal_error) | `8a4e039bb76f` (assertion, via metamorphic tlp_where) |
| found by arm | `grammar` (trial 2) | `llm_frag` (trial 2), i.e. the LLM-fragment arm (RQ4) |
| upstream master 4848fd675 (cassert) | ERROR | crash (TRAP, pathnode.c:1439) |
| master a39e53a70 (cassert) | ERROR | crash (TRAP, pathnode.c:1437) |
| 18.6 (no assertions) | ERROR | ok (assertion not compiled in) |
| 17.11 (cassert) | ERROR | crash (TRAP, pathnode.c:1328) |
| reproducer | `N1_merge_subplan.sql` | `N2_parallel_append_assert.sql` |

## N1: MERGE into a partitioned table, `ERROR: SubPlan found with no parent plan`

```sql
CREATE TABLE mp (a int, b text) PARTITION BY RANGE (a);
CREATE TABLE mp1 PARTITION OF mp FOR VALUES FROM (0) TO (10);
MERGE INTO mp t
USING (SELECT true AS c OFFSET 0) s ON t.a IS NULL
WHEN MATCHED THEN UPDATE SET b = (SELECT NULL WHERE s.c)
WHEN NOT MATCHED THEN INSERT VALUES (1, 'x');
-- ERROR:  SubPlan found with no parent plan     (17.11, 18.6, master)
```

Needed (each removal makes it succeed): a **partitioned** target (a plain table
works); a source subquery that is not pulled up (`OFFSET 0` or `LIMIT 1`); a
scalar subquery referencing the source in `UPDATE SET`; **both** `WHEN MATCHED
... UPDATE` and `WHEN NOT MATCHED ... INSERT` (either alone works; `DO NOTHING`
instead of INSERT works); a join condition that does not reference the source
(`ON t.a IS NULL`; `ON true` works). The equivalent `UPDATE ... FROM` works.

Related but different: commit eacee6b61 (2026-10-14, "Don't use SubPlan-containing
expressions for startup-time pruning") fixed the same error message for a SELECT on a
partitioned table (pruning with a const-folded SubPlan). That commit is in our
base and in 4848fd675, which still fail, so this MERGE case is not covered by it.

## N2: `TRAP: failed Assert("!parallel_aware || pathnode->path.parallel_safe")` in create_append_path

```sql
CREATE TABLE pi (a int);
CREATE TABLE pi_child () INHERITS (pi);
WITH c1 AS (SELECT 1 FROM pi WHERE true UNION ALL SELECT 1 FROM pi WHERE false),
     c2 AS MATERIALIZED (SELECT 1)
SELECT 1 FROM c1 UNION ALL SELECT 2 FROM c2;
-- server crash on assert-enabled builds (17.11, master)
```

Needed: an **inheritance parent** with a child (a plain table works); an inlined
CTE that is a UNION ALL with a **constant-false branch** (dummy rel; with only
true branches it works); an outer UNION ALL with a **MATERIALIZED CTE** scan
(parallel-restricted). Writing the first branch as a FROM subquery instead of a
CTE does not crash. A parallel-aware Append is built although one child is not
parallel-safe. Release builds (18.6) return the right rows, so the user-visible
impact is the assertion on debug builds (possibly a non-parallel-safe plan run
in a worker). The only earlier report of this assertion (pgsql-hackers, June 2018,
partitioned table + correlated subquery in max()) has a different trigger and was fixed.

## For the paper / RQ2 / RQ4

* Suggested verdicts for `triage/verdicts.yaml` (team decides): `3dc78dd95f41`
  real (new, BUG #19802), `8a4e039bb76f` real (new, pending report).
* N2 was found by the **LLM-fragment arm** through a metamorphic (TLP) rewrite.
* Other candidates of this run: BUG-01 (JSON_TABLE collations, ~12 signatures),
  upstream BUG #19784 (`c51c4dacc7f1`), upstream BUG #19772 (`84e36fe21cff`);
  the plan-variant / RLS wrong results inspected so far order by NULL / use
  `MODE()` with ties (order not defined), i.e. likely false positives.
