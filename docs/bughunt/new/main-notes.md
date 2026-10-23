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
