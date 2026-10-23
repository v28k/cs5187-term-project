# Hunter B: candidates, duplicates and features checked

## B-cand-1: wrong result in a chain of LEFT JOINs (DUPLICATE of BUG #19765, not ours to file)

Found 23 Oct 2026 by `fz2.py` (seed 101, query 7368) as a planner-setting difference:
count 54 with the default plan vs 9 with `enable_nestloop=off, enable_mergejoin=off`.
9 is correct (checked by hand); the default plan is wrong, on both master and 18.6.

Minimal form (both master 126976a8 and 18.6 return the wrong row `1 | 3 | | 3`):

```sql
CREATE TABLE ta (a int); CREATE TABLE tb (b int); CREATE TABLE tc (c int); CREATE TABLE td (d int);
INSERT INTO ta VALUES (3); INSERT INTO tb VALUES (1); INSERT INTO tc VALUES (3); INSERT INTO td VALUES (1);
SELECT * FROM td LEFT JOIN ta ON ta.a = 3 LEFT JOIN tb ON ta.a = tb.b LEFT JOIN tc ON tc.c = tb.b;
-- expected 1 | 3 | NULL | NULL: tb is null-extended, so tc.c = tb.b cannot hold
```

The plan has no join filter between `(ta LEFT JOIN tb)` and tc, only `Filter: (c = 3)` on tc.
Cause: `reconsider_outer_join_clauses()` (equivclass.c) propagates `ta.a = 3` → `tb.b = 3` →
`tc.c = 3` through the least-nulled clone of each outer-join clause (outer-join identity 3)
and replaces that clone by constant TRUE, but the join order chosen evaluates `tc` above the
null-extending join, where the clone's premise (`tb.b = 3` for every outer row) is false.

**Already reported upstream as BUG #19765** ("wrong result from a chain of left joins since
v16", 16 Oct 2026; same diagnosis by Tender Wang, Nitin Motiani and Richard Guo; patch under
discussion, nothing committed in master 126976a8). Mirror:
https://github.com/BharatDBPG/BharatDBMS-PG/issues/7771 . Our variant differs only in getting
the constant from a degenerate outer-join ON clause (`td LEFT JOIN ta ON ta.a = 3`) instead of
WHERE. That could be offered in the thread as an extra test for the fix. Do not file it as a new bug.

## Features audited, no bug found (23 Oct 2026, master 126976a8 vs 18.6)

- Outer join → anti join reductions (a812cf64, 2ce5a57b FULL→ANTI, 02119d6c whole-row
  IS NULL, f863be3e row IS NOT NULL strictness, ad4b80b6 redundant IS NULL removal): code
  read (forced_null_var_is_nonnullable, find_safe_quals, remove_redundant_nullability_quals);
  `fz1.py` ran 43,000 random nested LEFT/FULL/RIGHT/INNER joins with column, whole-row and
  composite IS [NOT] NULL, NOT IN, ROW() IS NULL and strict quals in RHS subqueries. About 10%
  of the queries were reduced to anti joins. 0 differences vs 18.6, 0 TRAPs.
- NOT IN → anti join (383eb21e): requires btree/hash operator, non-null outer exprs
  (nullingrels, inheritance, NOT VALID handled) and non-null subquery outputs. The only gap
  found is theoretical: an implicit cast on the sub-select side whose function returns NULL for
  non-null input (user-defined casts only). Not tested further.
- ROW(...) IS [NOT] NULL folding (cb7b7ec7) uses scalar per-field tests, matching
  ExecEvalRowNull (non-recursive). OK.
- Eager aggregation: grouping keys restricted to plain Vars with BTEQUALIMAGE true under
  the actual collation; join-key Vars checked the same way; EC reuse requires the same type
  (d764d61a). Nondeterministic-collation join/grouping combinations: eager aggregation is
  rejected, so there is nothing to break. Not fuzzed further.
- RI fast path (ri_FastPathCheck): btree only, index collation must equal column
  collation, operator must be in the index opfamily, FK type binary-coercible, ONLY semantics
  as in SPI. No functional gap found by reading; concurrency not tested.
- `fz2.py` (PHV-producing subqueries, LATERAL, UNION ALL, GROUP BY/DISTINCT subqueries,
  sort keys; master vs 18.6 plus random planner settings): 120,500 queries run. Findings:
  B-01 (reported) and B-cand-1 (duplicate). Diffs where 18.6 errors but master works were
  ignored (improvements).
