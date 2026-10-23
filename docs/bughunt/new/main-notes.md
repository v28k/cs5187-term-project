# Main session notes, 23 Oct 2026 (22:48-23:00 UTC)

Newest master built with assertions: commit 126976a8 (23 Oct 2026), server on port 5474.

## Checked, no bug found
- Hash joins with NULL join keys (new in commits 1811f1af9 and 126976a8, nodeHashjoin.c):
  LEFT, RIGHT and FULL joins, NOT EXISTS anti joins (both directions), two-key joins,
  extra non-hashable join filters, keys that evaluate to NULL (nullif, expressions),
  WHERE on the null-extended side, and hash joins rescanned inside LATERAL. Each was run
  under one-batch hash, multi-batch hash (work_mem=64kB), parallel hash, parallel
  multi-batch hash, and merge join, on 20,000-row tables with 20-25% NULL keys.
  All digests agreed.
- Planner support functions with NULL inputs: each expression compared with the
  (SELECT const) form that blocks the simplification: inet <<, <<=; LIKE '%';
  ILIKE; ~ ''; starts_with; array_append/prepend; timestamp/numeric/varchar
  length coercions. All agreed.

## Confirmed again
- BUG-02 (range containment with a NULL element) is still present on the newest
  master 126976a8 and on 18.6: 'empty'::int4range @> NULL gives f, and
  NULL::date <@ daterange(NULL,NULL) gives t. Both should be NULL. Not fixed upstream yet,
  so still fileable.

## Second round (22:55-23:08 UTC), pattern hunt (prefix E-)

### Checked, no bug found
- BUG-01 pattern (expressions transformed without assign_expr_collations): counted
  transformExpr vs collation assignment per parser file on newest master. parse_cte.c
  CYCLE mark values have no collation pass, but the grammar only accepts constants
  there (CYCLE ... SET m TO (expr) is a syntax error), so it cannot be reached.
- BUG-02 pattern (planner folds to a constant): read every makeBoolConst(true/false)
  site in optimizer/ and utils/adt. The NOT-NULL-based folding in eval_const_expressions
  (IS DISTINCT FROM, row IS [NOT] NULL, IS [NOT] UNKNOWN) relies on
  expr_is_nonnullable()/var_is_nonnullable(). Tested its risky cases, all correct
  on newest master:
  - virtual generated NOT NULL column of a partitioned table whose partition
    uses a different expression (fix d8444163 only touched the catalog path; the
    hash-table path is safe because columns are expanded before it is used:
    IS NULL, IS DISTINCT FROM, NOT IN, COALESCE, row IS NOT NULL all correct);
  - ARRAY[x] with NULL sub-arrays (gives {}, never NULL, so the ArrayExpr rule holds);
  - IS DISTINCT FROM with a user-defined = that returns NULL (same answer with and
    without folding, same as 18.6);
  - MERGE ... WHEN NOT MATCHED BY SOURCE cannot reference source columns (rejected).
- Hash join NULL keys: confirmed with EXPLAIN ANALYZE that the earlier test ran a
  Parallel Hash Full Join with 4 workers and 8 batches; results matched merge join.

### Confirmed again
- BUG-01 is still unfixed on newest master 126976a8 (parse_jsontable.c line 157 has
  no assign_expr_collations after transformExpr of the context item).
- The overnight campaign hit BUG-01 on its own: candidate a3b2c7023c02
  (cross-version, 145 vs 142 rows) comes from an earlier INSERT whose JSON_TABLE
  context item contains GREATEST('x%'::text, 'W'::text). 18.6 fails it with
  "could not determine which collation to use for string comparison", so t3 has one
  row fewer there. This is extra evidence for BUG-01, not a new bug.
  (The 5434 master build includes our BUG-01 patch, so it succeeds there.)

### Third round (23:00 UTC): BUG-01 pattern in other FROM-clause constructs
Row and text comparisons on newest master 126976a8 and 18.6 inside TABLESAMPLE arguments,
REPEATABLE, ROWS FROM function arguments, JSON_TABLE column DEFAULT ... ON EMPTY,
JSON_QUERY/JSON_EXISTS/JSON_VALUE PASSING, and window RANGE offsets: all correct.
JSON_TABLE PASSING with a row comparison still hits BUG-01's assertion on newest
master (execExpr.c:2078); this is BUG-01's documented PASSING case, not new.
XMLTABLE is untested: the newest master build has no libxml. SQL/PGQ (GRAPH_TABLE) is
not in master yet.
