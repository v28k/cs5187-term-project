# Results of the final campaigns (analysis, 29 Oct 2026)

Single source for the numbers used in the paper, slides and guide. Raw data:
`runs/memberA-rq3/` (RQ3, member A's laptop) and `runs/memberB-rq1-llm/` (LLM arm
and RQ1/RQ2, member B's laptop). Both merged into `main` (`a0adcd9`, `f2574db`).
All campaigns: master `26bd08fb` (assertions on), 5 trials x 1 h per arm, `-j 4`,
reference server 18.6. **No source file was changed by the members**; the Gemini
substitution is a driver script outside `src/` (see "Deviations").

## Deviations from the plan (must be stated in the paper)

1. **The LLM was Google Gemini, not Claude.** No Anthropic key was available.
   `pgfuzz llm extend --mode manual` wrote each prompt; `runs/memberB-rq1-llm/llm_driver/gemini_driver.py`
   sent it to the Gemini API (free tier) and stored the JSON answer. Served models:
   9 x `gemini-3.6-flash`, 2 x `gemini-3.8-flash`, 14 x `gemini-3-flash-preview`
   (25 rounds; Pro models have no free quota; the driver falls back to the next model
   on quota or repeated 503). Cost 0 USD (tokens still counted). 10 commits instead of 30
   because of the daily quota (25 commits mined, the first 10 used). The ledger marks
   rounds `replayed: true` only because manual mode reads the answer file; every answer is fresh.
   Every statement "Claude Opus 5.5 is the model" in earlier drafts is wrong for the results.
2. **RQ1 ran on member B's machine, RQ3 on member A's**, never mixed (each experiment on one machine).
   B: WSL2, 24 cores, `-j 4`. See each `env.txt`.
3. **B's campaign hit infrastructure incidents** (`NOTES.md`): worker 2's server failed
   crash recovery after a BUG-01 assertion (`could not create file "base/5/499854": File exists`;
   same signature as our unreproduced "candidate 2", now known upstream as BUG #17731);
   14 trials failed at connect and were re-run with the same seeds; laptop sleep ~03:00-10:30
   (trial clocks are monotonic, so each trial still got 3600 s).
4. The fixes to the tool listed below were made **after** the campaigns. Campaign numbers
   are "before" figures; the fixes were validated on the stored reproducers and by unit tests, not by re-running.

## RQ1: reach (medians of 5 trials; `runs/memberB-rq1-llm/report/`)

| Arm | Line cov. | Branch cov. | SQL features | Plan shapes | Valid stmts | Test cases |
|---|---|---|---|---|---|---|
| Random/Mutation | 22.2% | 15.1% | 23 | 43 | 26.0% | 1,074,240 |
| Grammar | 36.7% | 27.1% | 101 | 20,279 | 99.3% | 71,228 |
| Grammar+Oracles | 36.2% | 26.7% | 101 | 34,313 | 96.3% | 58,601 |
| Grammar+Oracles, no bandit | 36.2% | 26.8% | 101 | 23,997 | 99.4% | 64,923 |
| +LLM fragments | 35.7% | 26.5% | 104 | 25,972 | 95.5% | 48,222 |
| +LLM seeds | 35.6% | 26.4% | 106 | 29,274 | 98.3% | 63,655 |
| Grammar+Oracles+LLM | 35.7% | 26.4% | 106 | 26,375 | 95.3% | 46,754 |

* Grammar vs Random: every reach metric large (A12 = 1.00; p = 0.007-0.012, the minimum for 5 vs 5 is 0.008).
  Random runs 15x more test cases (1.07M vs 71k) and reaches 23 features and 43 plan shapes.
* Oracles do **not** raise line coverage (36.7% -> 36.2%, p = 0.42); they roughly **double plan shapes**
  (20,279 -> 34,313, A12 = 0.84, p = 0.095, not significant at 5 trials) and cost throughput (67 -> 40 statements/s).
* Bandit weights: plan shapes 23,997 -> 34,313 (A12 = 0.80, p = 0.15) at slightly lower validity (99.4% -> 96.3%, p = 0.016).
* LLM arms vs matching baseline (Grammar+Oracles): **+5 SQL features** (101 -> 106, A12 = 1.00, p = 0.004), but line
  coverage 36.2% -> 35.7% (p = 0.42), plan shapes 34,313 -> 26,375 (p = 0.69), validity 96.3% -> 95.3%. **No coverage gain.**

## RQ3: re-injected bugs (`runs/memberA-rq3/`)

* Verified benchmark: 20 of 23 observable (8 wrong result, 5 internal error, 4 assertion, 2 missing error, 1 wrong error).
* Found: **rb-dfcf6fa7** (internal error): Grammar 5/5 (median 458 s), Grammar+Oracles 4/5 (509 s), +LLM 5/5 (1,109 s), Random 0/5.
  **rb-11b56ee2** (assertion pathkeys.c): Grammar+Oracles 1/5 (2,901 s), +LLM 1/5 (1,858 s).
* Bugs found: Random 0/20, Grammar 1/20, Grammar+Oracles 2/20, +LLM 2/20. **No wrong-result benchmark bug was found by any arm (0/8)**;
  the other 17 bugs by none.
* 56 failures recorded; of its 30 wrong-result failures, 11 reproduce on the fixed server, 19 on no server, none on a solo server;
  triage of the 41 candidates (all outcomes): 21 flaky, 20 reproducible (see RQ2).
* Interpretation to write honestly: 1 h x 5 trials is short for bugs needing specific feature combinations; the strongest
  evidence for the oracles is in RQ2 (real wrong results found), not RQ3.
* Cost of oracles visible in RQ3 too: Grammar finds 7 candidates (median), Grammar+Oracles 2 (most are false positives).

## RQ4: LLM arm (`logs/B2_llm_report.txt`, `llm/ledger.jsonl`)

10 commits, 4 accepted (40%): 2 in round 1, 1 in round 2, 1 in round 3; 25 rounds;
rejections by stage: validity 16, reachability 2, parse 2, coverage/seeds 1; mean validity of proposals 0.365;
diff-coverage gain 34 changed lines in total; tokens 327,856 in / 170,931 out / 46,568 cached; cost 0 USD (free tier);
7 of 7 proposed rewrites accepted by the gate; 0 gate bug candidates.
Findings:
* The gate works as a filter: 16 of 25 rounds rejected on server validity.
* The gate is **not sufficient for rewrites**: the accepted rewrite `NULLIF({e}, NULL::text COLLATE "POSIX")`
  (commit d8ce0050a6) produced a false positive (`UPPER('e-acute')` differs); the value probe and 150 live checks do not
  test collation. Fixed in the tool: gate rejects explicit COLLATE.
* The LLM-fragment arm found upstream-confirmed BUG #19803 (signature `8a4e039bb76f`, via a TLP check), and arm `+LLM seeds`
  had the most bug candidates (median 3 vs 1; p = 0.29, not significant).
* Honest verdict: modest. More features, no coverage gain, lower validity, 4 of 10 commits usable, model weaker than planned.

## RQ2: bugs and oracle precision (`triage/verdicts.yaml`, 93 candidates)

Unique candidates of the two campaigns: 77 signatures (A: 41, B: 42, overlap), plus the 18 earlier ones.
Triage reproduces x3: 28 flaky.

| Verdict | Count |
|---|---|
| real | 7 |
| duplicate (real bug already reported upstream) | 15 |
| false positive | 36 |
| not a bug (intended change) | 1 |
| flaky | 28 |
| undecided (TODO) | 6 |

False-positive classes found in the final campaigns (all fixed in the tool after the runs, 10 new tests; stored reproducers rechecked):
1. **Equal intervals with different text** (`MODE() WITHIN GROUP` over intervals, `UNION`, `INTERSECT ALL`): 16 candidates.
   Not ties: all 357 keys were equal values (`00:00:00` vs `6 days -144:00:00`); which representative is returned depends on join order.
   Fix: interval digests compare by PostgreSQL's own equality (month = 30 days, day = 24 h).
2. **Order-sensitive aggregate with a non-total ORDER BY** (`JSONB_AGG(x ORDER BY NULL)`): 2. Fix: the sort key must be the aggregate's own argument.
3. **Cross-version state divergence**: `LAG(...) IGNORE NULLS` (PG19-only) inside an INSERT succeeds on master, fails on 18.6, so later SELECTs differ: 5.
   Fix: stop comparing after a state-changing statement succeeds on one server only.
4. **LLM rewrite that changes the collation** (above): 1. Fix: gate rejects COLLATE.
* 5 RLS candidates stay **undecided**: they are not explained by class 2 (sort key equals the aggregated value). Verify at the end.
* 1 more undecided: `corr(1.0/3, 1.0/3)` is NULL serially but 1 under partitionwise/parallel aggregation on master
  (`float8_regr_combine` recomputes Sxx from rounded means although the accumulate function keeps it exactly zero for constant input;
  commit 649828769). Reproduced on 126976a8, not on 18.x. A fix mirroring `float8_regr_accum` is sketched in the scratchpad
  (not applied, not tested, **not searched upstream beyond the original thread**). Candidate new bug; verify at the end.

Precision (decided = real + false positive + not a bug; duplicates counted neither side): 7 / 44 = 0.16 before fixes;
counting duplicates as true positives (they are real bugs the oracles found): 22 / 59 = 0.37. After the fixes to the tool: every
decided candidate left is real (the paper must say this is post hoc and not re-measured by a campaign).

### Real bugs and duplicates behind these numbers

| Bug | Found by | Upstream | Status (29 Oct) |
|---|---|---|---|
| BUG-01 JSON_TABLE collations | grammar arm, 10 signatures | #19768 | filed 16 Oct, no committer reply recorded |
| BUG-02 range containment NULL | metamorphic `expr:scalar_sub` | #19793 | filed 23 Oct, patch sent |
| N1 MERGE "SubPlan found with no parent plan" | grammar arm (`3dc78dd95f41`) | **#19802** | **confirmed by Tender Wang**, patch posted |
| N2 Parallel Append assertion | LLM-fragment arm via TLP (`8a4e039bb76f`) | **#19803** | **confirmed by David Rowley; fixed on master in `abda2a2c`** |
| C-01 dependencies.c assertion | hunter C | pgsql-bugs | filed 27 Oct |
| AUDIT-F1 NOT IN anti-join cast; AUDIT-F2 IGNORE NULLS hang | audit | pgsql-bugs | filed 23 Oct (F2: Ishii replied) |
| #19766 shm_toc assertion | grammar arm | #19766 | reply sent |
| duplicates rediscovered by the oracles | plan-variant (SJE off/on) -> **#19800**; `e` vs `(SELECT e)` -> **#19772**; `c51c4dacc7f1` -> **#19784**; to_char NaN crash -> **#19771** (fixed 776df8a6) | | reported by others first |

* `to_char`/`NORMALIZE` crash (`efa9efb8acc1`, grammar arm, reduced to 27 tokens): crashes on the base commit, not on 126976a8.
  The fix commit 776df8a6 (BUG #19771) lists author **"Gowtham Reddy <gowthamdoma18@gmail.com>"** (assumed to be the team member:
  **confirm with Gowtham**; if true, that is an upstream-accepted and committed fix by a team member, strongest evidence for the grade).
* The self-join-elimination duplicate (#19800) shows the plan-variant oracle finding a real released-version wrong result
  (18.6 and master): `a2.v IS NULL` over `ROLLUP` subtotal rows is `f` with SJE on, `t` with it off. Our symptom (SELECT-list
  values, not only ORDER BY) can be added to that thread.
* Not filed (decision by the team): B-01 FULL JOIN after NOT NULL folding (hackers thread 7400 in progress).

## Things to do before submission (open)

1. Confirm authorship of 776df8a6 with Gowtham; collect upstream status links (BUG numbers above) into the paper's data section.
2. Verify at the end (user decision): the 5 RLS candidates, the `corr` parallel case, and re-run the BUG-01/02 reproducers.
3. Google Drive link for the 110 MB archive of B (`LINKS.md` still TODO) and A's archive.
4. Paper: fill RQ1-RQ4, abstract, intro, conclusion, data availability; AI statement (Gemini for the LLM arm; Claude Code for coding/drafting); cut to the page limit.
5. Update guide, slides and PPTX with the final numbers and screenshots (member screenshots are in `runs/*/screenshots/`).
