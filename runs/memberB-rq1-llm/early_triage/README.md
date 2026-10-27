# Early triage of the B3 (RQ1) candidates, 27 Oct 19:00–19:30

Done while B3 was running, on separate scratch servers (ports 5496–5498), so the
campaign's coverage servers were not touched. The official B4 triage still runs
after the campaign.

| signature | oracle | arms | verdict |
|---|---|---|---|
| `cde9712bc8db` | assertion `list_length(rcexpr->inputcollids) == nopers`, execExpr.c:2078, under `ExecInitTableFuncScan` | grammar_mm, grammar_mm_flat | **duplicate of BUG-01** (JSON_TABLE collations), already `real` in `triage/verdicts.yaml` |
| `c51c4dacc7f1` | internal error `XX000 no relation entry for relid 1` | grammar | **new candidate, looks real**; not in known_bugs, verdicts, bughunt docs or upstream master log (checked up to 700b422af, 2026-10-27) |

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
