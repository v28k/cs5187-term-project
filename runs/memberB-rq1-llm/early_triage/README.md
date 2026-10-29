# Early triage of the B3 (RQ1) candidates, 27 Oct 19:00–19:30

Done while B3 was running, on separate scratch servers (ports 5496–5498), so the
campaign's coverage servers were not touched. The official B4 triage still runs
after the campaign.

| signature | oracle | arms | verdict |
|---|---|---|---|
| `cde9712bc8db` | assertion `list_length(rcexpr->inputcollids) == nopers`, execExpr.c:2078, under `ExecInitTableFuncScan` | grammar_mm, grammar_mm_flat | **duplicate of BUG-01** (JSON_TABLE collations), already `real` in `triage/verdicts.yaml` |
| `c51c4dacc7f1` | internal error `XX000 no relation entry for relid 1` | grammar | **real, but duplicate of upstream BUG #19784** (reported 2026-10-21 by Alperen Keles; Tom Lane patch 2026-10-22, not committed yet); fixed by the local #19784 patched build |

## c51c4dacc7f1: MIN/MAX index optimization + pushed-down `= ANY(<function>)`

Minimal reproducer (no project schema needed):

```sql
CREATE TABLE m(a int);
CREATE INDEX ON m(a);
SELECT 1 FROM (SELECT max(a) AS c FROM m) s WHERE 7 = ANY (array_append('{}', c));
-- ERROR:  no relation entry for relid 1
```

| server | result |
|---|---|
| 17.11 | ERROR no relation entry for relid 1 |
| 18.6 | ERROR no relation entry for relid 1 |
| master 20devel a39e53a70 (cassert) | ERROR no relation entry for relid 1 |
| latest upstream master 700b422af | not built yet (would slow B3); do after B3 |

What is needed (each removal makes the query succeed):

* `min()`/`max()` of an **indexed** column in a subquery (MIN/MAX-to-index
  optimization, planagg.c). Without the index, or with `max(a)` of a plain
  table with no index, it works.
* an outer `x = ANY(arr)` / `x <> ALL(arr)` whose array is a **function call**
  (`array_append`, `array_cat`, `array_positions`). `= ANY(ARRAY[c])` works.
* the qual must be **pushed down** into the aggregate subquery: adding
  `OFFSET 0` to the subquery makes it work.
* `enable_indexscan/indexonlyscan = off` does **not** help, so the error comes
  during planning (likely selectivity estimation of the pushed-down
  ScalarArrayOpExpr once planagg has rewritten the aggregate), not execution.

Files: `c51c4dacc7f1/reduced.sql` (pgfuzz triage tree+token reduction, 357 -> 68
tokens), `c51c4dacc7f1/upstream_report.txt` (template), original
`testcase.sql` and `failure.json`.

Next: confirm on latest master after B3, find the failing `find_base_rel()` call
with a backtrace (`\set VERBOSITY verbose` gives the source location), search
pgsql-bugs, then add the verdict to `triage/verdicts.yaml` (team).

## Update: duplicate of BUG #19784 (checked 27 Oct)

* pgsql-bugs **BUG #19784** (2026-10-21, Alperen Keles, 18.6): "no relation entry for
  relid 1" when costing `= ANY (<array expr over max(col)>)` in a MinMaxAggPath; lists
  our exact shape (aggregate in a FROM subquery, qual pushed down from the outer WHERE).
  Cause per the report: `preprocess_minmax_aggregates()` costs the tlist/HAVING before
  baserels exist; `estimate_array_length()` -> `examine_variable()` -> `find_base_rel()`.
  First bad commit per the reporter: 9391f7152 (estimate_array_length uses statistics).
  Tom Lane posted a patch (2026-10-22), Shihao Zhong a follow-up (2026-10-23); no commit yet.
  Mirror: https://github.com/BharatDBPG/BharatDBMS-PG/issues/7857
* The team already tracks it: bugprogress/C-progress.md item U4.
* `~/pgfuzz/install/p19784` (master 126976a8f + Tom's selfuncs.c patch): our reduced
  query returns 1 row, the report's repro returns f, and the original fuzzer test case
  runs without error. So c51c4dacc7f1 is the same bug.

Verdict for triage/verdicts.yaml: `duplicate` (real bug, upstream BUG #19784, found
independently by the grammar arm).
