# Validation of the bug-hunt-2 results (23 Oct 2026, end of hunt)

Builds used: newest master 126976a8 (cassert, port 5474), newest REL_18_STABLE
9412c35 (cassert, port 5476), 18.6 release (port 5435). Fresh database `val` on each.

## Hunter A (mutating the 23 recently fixed bugs)
Stopped. It pushed no report and no candidates file, and its server
(/home/pg/hunt/h5471) logged no assertion failure. Result: nothing to file.

## Overnight campaigns (stopped after ~40 min)
| Candidate | Campaign | Kind | Verdict |
|---|---|---|---|
| a3b2c7023c02, a666c463ba86, e1fc243acce1 | hunt2a (master with BUG-01 patch vs 18.6) | cross-version, 145 vs 142 rows | BUG-01: statement 5 inserts through JSON_TABLE; master accepts it, 18.6 rejects it with "could not determine which collation to use for string comparison", so t3 has one row fewer on 18.6 |
| cde9712bc8db, f6f5012e736d, 74de1db17561 | hunt2b (unpatched master 26bd08fb) | assertion | BUG-01: all 85 TRAPs in the server log are Assert("list_length(rcexpr->inputcollids) == nopers"), execExpr.c:2078, under ExecInitTableFuncScan; signatures differ only by the plan node above (Sort, Limit) |
Result: no new bug; six more independent rediscoveries of BUG-01.

## Reports from the other chats, re-run here
| Report | Newest master | Newest REL_18_STABLE | 18.6 | Verdict |
|---|---|---|---|---|
| B-01 FULL JOIN fails after NOT NULL folding | all 5 FULL JOIN queries fail: "FULL JOIN is only supported with merge-joinable or hash-joinable join conditions" | all answer | all answer | reproduced: regression in 19/master |
| C-01 dependencies.c assertion with duplicate statistics expression | backend crash, TRAP dependencies.c:1504 | backend crash, TRAP dependencies.c:1525 | release build: plans normally | reproduced on both assert builds |

## Mine
| Report | Newest master | Newest REL_18_STABLE | 18.6 |
|---|---|---|---|
| BUG-01 JSON_TABLE collations | present | present | present |
| BUG-02 range containment with NULL element | present | present | present |
