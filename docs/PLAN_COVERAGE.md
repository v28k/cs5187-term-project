# From plan to code: every promise of meeting 1, where it is, and the evidence

Sources: `progressmeet1/future_plan.pdf` (Study guide 2, 16 Oct) and
`progressmeet1/slides.pdf` (meeting 1). Status on 24 Oct 2026. "Evidence" is a
measurement from a real run on PostgreSQL master `26bd08fb` unless it says
"unit test".

## The three claims (slides 6, plan 0.3)

| Claim | Status | Where | Evidence |
|---|---|---|---|
| **One tree, four jobs**: generation, mutation, metamorphic rewrite, reduction on the derivation tree | done, all four | `grammar/engine.py` (spans, `MINIMAL` marker), `grammar/generator.py` (replay), `grammar/rewrite.py`, `triage/tree_reduce.py`, `grammar/treeio.py` | BUG-01 case: 116 tokens (token reduction) vs **79 tokens** (tree then token); 599/600 test cases replay identically in a fresh process (`docs/evidence/tree_reduction/`) |
| **Soundness we measure**: generator validity, oracle precision | done | `eval/metrics.py`, `triage/precision.py`, `triage/verdicts.yaml` | validity 99.6-99.7 % on master; precision ledger of 18 triaged candidates, before/after fixing each false-positive class |
| **The LLM proposes; the server decides** | done, extended to oracle rewrites | `llm/gate.py`, `llm/loop.py` | live gate: valid fragment accepted, invalid rejected with the server's own error; rewrite gate accepts identities, rejects `e+1` (12 mismatches) and `e IS TRUE` (value probe) |
| Localization from plan oracle x rewrite oracle (plan 0.3) | done | `triage/localize.py` | BUG-02 localized to "not toggled by planner settings" = the planner support function, its true cause |

## Plan item by item

| Plan section | Item | Status | Where / evidence |
|---|---|---|---|
| 0.1-1, 2 | Grammar arm tuned and fuzzing for hours | done | 6-hour hunts; 99.7 % valid statements |
| 0.1-2, 3.2 | TLP (WHERE, DISTINCT via UNION, HAVING) | done | `rewrite._tlp_where/_tlp_having`; also inside derived tables, CTEs, set arms, IN/EXISTS/LATERAL |
| 3.2 | TLP variants for aggregates (MIN/MAX, SUM of SUMs, SUM of COUNTs) | **done (new)** | `rewrite._tlp_agg` (+ `BIT_*`, `BOOL_*`, `EVERY`) |
| 3.3 | NoREC | done | `rewrite._norec` |
| 3.4 | `x IN (a,b,c)` <-> `x=a OR x=b OR x=c` (OR-to-ANY) | **done (new)** | `rewrite._pred` (`pred:in_or`) |
| 3.4 | `p -> p AND c IS NOT NULL` for a NOT NULL column | **done (new)** | `rewrite._notnull` (not under outer joins, not for generated columns) |
| 3.4 | CTE `MATERIALIZED` toggle | done | `rewrite._cte` |
| 3.4 | `e -> CASE WHEN true THEN e END`, `e -> (SELECT e)` | done | `rewrite._ANY` (found BUG-02) |
| 3.4 | `a < b -> NOT (a >= b)` | **done (new)** | `pred:cmp_negate` (exact under 3VL, no guard needed) |
| 3.4 | `t -> (SELECT * FROM t)` subquery flattening | done | `table_fence` (`OFFSET 0`) |
| 3.4 | ORDER BY removed when compared as a multiset | **done (new)** | `rewrite._order_drop` |
| 3.4 | BETWEEN expansion (extra) | **done (new)** | `pred:between` |
| 3.4 | "letting the LLM add new rewrites is our contribution" | **done (new)** | prompt `rewrites` field; `gate.check_rewrites` (value probe + 150 live test cases, zero mismatches); `results/llm/rewrites` feed the LLM arms |
| 3.4 | `t JOIN s ON k` -> `WHERE EXISTS` for unique `s.k` | not done | needs uniqueness proofs over joins; join removal is exercised by the table fence and `no_self_join_elim` / plan variants instead |
| 3.5 | Reuse `eligible()` determinism filter and digests | done | `eval/differential.py` |
| 3.5 | At most 1-2 rewrites per query | done | `mm_per_query` |
| 3.5 | Re-run both sides before reporting | done | `mm_confirm` |
| 3.5 | Re-run under planner variants: planner bug vs executor/rewrite bug | **done (new)** | `triage/localize.py`, in every triage report |
| 4 | Cross-version differential (release vs master) | done | `reference/xversion_executor.py` (18.6; REL_19 does not exist yet), per-worker reference DB, intended changes excluded (`corr/regr_*`) |
| 5.1 | Commit miner since the branch point | done | `llm/commits.py` (`--exclude` keeps benchmark fixes away from the model) |
| 5.1 | LLM proposes grammar edits and seeds | done | `llm/prompt.py`, `llm/client.py` (API or manual mode, stored responses) |
| 5.1 | Validation gate: parse, sample, validity, coverage of changed lines | done | `llm/gate.py` |
| 5.2 | Diff coverage metric | done | `llm/diffcov.py`, per-worker gcov counters (`scripts/rq1_servers.sh`) |
| 5.3 | Feedback-weighted alternatives (bandit) | **done (new)** | `generator._bandit_update`; one run: 533 vs 419 plan shapes at equal validity; ablation arm `grammar_mm_flat` in RQ1 |
| 5.4 | Acceptance rate, token cost, coverage per patch | done | `pgfuzz llm report` (ledger) |
| 5.5 | Hot targets: eager aggregation needs a GUC variant | **done (new)** | plan variant `no_eager_agg` (18 variants now) |
| 5.5 | Skip scan, OR-to-ANY, virtual generated columns, RETURNING OLD/NEW, MERGE, JSON_TABLE, partitionwise | in grammar | multi-column indexes, `pred:in_or`, table `t4`, grammar rules |
| 6 | Plan-shape novelty feedback (QPG) | done | `plan_shapes` in executor, corpus reason `plan` |
| 6 | Boundary literals from interval analysis (L19-20) | **done (new)** | `grammar/profile.py`: observed min/max +-1, type edges (NaN, +-Infinity, -0, extremes, empty array) |
| 6 | Data-aware predicates with target selectivity (L27-28) | **done (new)** | `pgfuzz profile` + `@dlit(T)`: predicates selecting 5-95 % of rows **29.3 % -> 58.6 %** |
| 6 | Schema churn (ANALYZE, indexes, tables between queries) | done | `setup_stmt` rules (VACUUM cannot run inside the test transaction) |
| 7.1 | Reproduce x3, park flaky | done | `triage --repeat 3` |
| 7.2 | Grammar-tree reduction, then ddmin on statements and tokens | **done (tree part new)** | `triage/tree_reduce.py` + `triage/reduce.py` |
| 7.3 | Classify crash / assertion / XX000 / wrong result | done | `eval/oracle.py` (+ crashes of other sessions no longer blamed) |
| 7.4 | Bisect | done | `scripts/bisect_pg.sh` |
| 7.5 | Check the latest release | done | `--reference`, cross-version oracle |
| 7.6 | Dedup against pgsql-bugs / hackers archives | manual | checklist in every `report.md` (archives are not reachable from the fuzzing machines) |
| 7.7 | Report with a fixed template | **done (new)** | `upstream_report.txt` per candidate |
| 7.8 | Precision per oracle (L5) | done | `pgfuzz precision`, before and after fixed classes |
| 8.1 | RQ1-RQ4 | designed, configs ready | `configs/rq1.yaml` (7 arms), `configs/rq3.yaml` (4 arms) |
| 8.2 | Re-injected bug benchmark, 8-12 fixes | **done, 23 fixes (20 observable)** | `bench/reinjected/`, `scripts/build_reinjected.sh`, `pgfuzz bench verify/attribute` |
| 8.3 | Medians with 95 % CI, Mann-Whitney U, A12 | **done (CI new)** | `eval/stats.py` (`median_ci`), report tables |
| 8.4 | Five graded paper parts | drafted | `paper/` (motivating example = BUG-02, a real new bug) |
| 9 (L3, L21-22) | Stretch: RLS leak oracle (information flow) | **done (new)** | `corpus/rls.sql`, kind `rls`: 532 live checks, 0 false positives |
| 0.1-7 | Stretch: CERT-style performance oracle | **done (new)** | kind `cert`, outcome `performance` |

## Beyond the plan (added to raise the level)

| Addition | Why it matters |
|---|---|
| Value probe for LLM rewrites | sampling alone accepted the false identity `e IS TRUE` (109 checks); the probe rejects it at NULL: a measured lesson for the paper (Observation 1) |
| Foreign-crash filter (PID matching) | a crash caused by another session is no longer blamed on the running test case: found by our own smoke run |
| Numeric-scale / float `-0` canonical digests | removed a false-positive class that a richer grammar exposes |
| Pinned base commit for all RQs | RQ1-RQ4 and diff coverage measure the same code |
| Per-worker gcov counters and reference databases | parallel trials cannot contaminate each other |
| Upstream report drafts and localization | shortens the path from a candidate to an accepted bug (the 50 % component) |

## Honest gaps

* `t JOIN s` -> `EXISTS` rewrite (needs uniqueness reasoning; covered indirectly).
* Archive de-duplication is a manual checklist step.
* The paper is over the page limit until the result tables decide what to cut.
* Every number above is a component check; the campaign numbers (RQ1-RQ4) come
  from `docs/EXECUTION_PLAN.md`.
