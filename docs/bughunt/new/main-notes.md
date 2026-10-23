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

## Fourth round (continued hunt), all on newest master 126976a8

### Checked, no bug found
- Eager aggregation and binary-image equality (sibling of fix d764d61a): join on the
  record image operator *= with numeric fields of different scale. Both grouping
  branches (GROUP BY expression, and extra join key) require the type's
  BTEQUALIMAGE proc, so numeric/record keys are refused. Results correct.
- Eager aggregation and non-deterministic collations (sibling of d237a7a8, semijoin
  unique-ification by the wrong collation). Built newest master with ICU (port 5475).
  Join compares with "C", the column is case-insensitive (und-u-ks-level2), in 5
  GROUP BY forms: eager aggregation is never chosen (the equalimage check uses the
  column's collation), results correct. Control: with a deterministic column, eager
  aggregation is chosen (Partial HashAggregate).
- Self-join elimination (on vs off): unique columns with NULLs, NULLS NOT DISTINCT,
  partial unique index, extra join filters, nested outer join, LATERAL, FOR UPDATE,
  window functions, sublinks, and UPDATE/DELETE/MERGE with RETURNING old/new.
  All identical.
- NOT IN to anti-join conversion (383eb21eb, query_outputs_are_not_nullable):
  22 subquery shapes (nullable sides of LEFT/RIGHT/FULL joins, ON-clause quals of
  outer joins, join alias columns, USING merged columns, IS NOT FALSE / IS NOT TRUE /
  IS DISTINCT FROM / coalesce / OR quals, LATERAL, GROUP BY, CASE, greatest) plus 8
  outer-side cases (outer expression on the nullable side, correlated outputs, row
  NOT IN, casts, UNION ALL with NULL). Oracle: NOT (x = ANY (ARRAY(subq))). All equal.
- Functions overwriting their caller's fcinfo->args (sibling of e355089a,
  jsonb_set_lax use-after-free): no other SQL-callable function does it (the other
  hits build their own call frames).
- ILIKE in single-byte encodings (sibling of c00a97b6): LATIN1 database, C locale,
  non-ASCII letters: ILIKE vs lower() LIKE lower() for 11 patterns, ESCAPE with
  non-ASCII escape characters, ~* and ~, index scan vs seq scan: all consistent.

## Fifth round

### Checked, no bug found
- PlaceHolderVar fixes of this week (3138f248 RTE_RESULT removal, 7787aec8 outer-join
  commutation): 18 mutants of 3138f248's tests and 12 mutants of 7787aec8's test (more
  nesting, FULL/RIGHT joins, EXISTS, grouping sets/rollup/cube, window functions,
  sublinks, VALUES, extra outer joins, coalesce/strict clauses). Newest master gives
  the same results as OFFSET 0-fenced equivalents, with no assertion failures. 18.6
  fails 8 of them with "failed to build any N-way joins" (fixed by 3138f248, which is
  backpatched to 14). Built newest REL_18_STABLE (9412c35, cassert, port 5476): it
  gives master's results for all 18, so the backpatch also covers our mutants.
- 12 PHV queries over partitioned tables (LATERAL, coalesce from nullable side,
  GROUP BY/DISTINCT/ORDER BY on the PHV, FULL JOIN, UNION ALL, window) under 7
  planner configurations (partitionwise, merge only, no hashagg/sort, parallel, ...):
  no errors, identical multisets.
- Hash join null-keyed tuples (126976a8) with filters: WHERE conditions evaluated at
  the join, extra ON conditions, NOT EXISTS with conditions, row-valued keys,
  RIGHT join: 5 join methods agree on all 8 queries.
- to_char() with formats ending in a decimal point (sibling of 776df8a6) for int4,
  int8, float4, float8, numeric and D/PR/MI/PL/TH/SG suffixes: consistent across
  types and with the fix's expected output. (TH after a decimal point is suppressed,
  as on 18.6; EEEE followed by a literal drops the literal, but the docs require
  EEEE to end the format.)
- Query jumbling of SQL/JSON (pg_stat_statements on newest master): no assertion
  failures; normalised texts correct for JSON_VALUE/QUERY/EXISTS/OBJECT/ARRAY/aggs/
  MERGE RETURNING/IN lists.

### Found but already reported upstream (duplicate, do not file)
- JSON_TABLE column definitions are left out of the query ID (TableFunc.colvalexprs,
  coltypes, coldefexprs, passingvalexprs and plan are query_jumble_ignore). Queries with
  different column types, paths, ON ERROR behaviour, NESTED PATH or extra columns get
  the same query identifier (4688385417845523979 for 8 different queries on master
  and on 18.6), although one of them raises an error and the others do not.
  Reported on pgsql-bugs by Ilya Staroverov in October 2026, patch under discussion:
  https://www.postgresql.org/message-id/457969A9-5D24-422F-B09E-F388053DE028%40localhost.localdomain
- The overnight campaigns keep rediscovering BUG-01 (hunt2b assertion
  cde9712bc8db, hunt2a cross-version candidates a666c463ba86, e1fc243acce1).
