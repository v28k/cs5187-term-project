# Speaker notes: progress meeting 2

One section per slide, in order. The slide numbers match progress_meeting2.pptx.

## Slide 1: Title

Last time (16 Oct) we presented the question and a plan. Today: the plan is executed. The system is built, it found real PostgreSQL bugs, and the campaigns are measured.

## Slide 2: Where we were last time

Our question: can a typed grammar, extended by an LLM that reads PostgreSQL's commits, find more bugs than random mutation and a plain grammar under the same budget? On 16 Oct we had a working harness, 100% valid statements on 300 test cases, and no bugs yet. The three claims are what the rest of the talk checks.

## Slide 3: Plan versus what we did

Go row by row. Things we changed honestly: 5 trials per arm instead of 10 because of the time budget, and the gate threshold was calibrated to 60% valid. We exceeded the benchmark size (23 vs 8-12) and met the target of at least one bug acknowledged upstream: four new bugs, two confirmed, one fixed.

## Slide 4: Build 1: a typed grammar that keeps the tree

Generation builds a derivation tree. Each node knows its type and scope. Mutation re-derives one subtree; oracles rewrite one node; triage reduces it. Because the node has a type, any replacement stays valid SQL. 78 rules, 421 alternatives, 13 types, and a 9-table schema with partitions, inheritance, a view and four index types.

## Slide 5: Build 2: oracles that know the right answer

A crash fuzzer only notices crashes. For silent wrong results we need an oracle. Ternary logic partitioning: every row makes a predicate true, false or NULL, exactly one. So the query must equal the union of the three partitions. If not, the planner or executor is wrong. We have 12 such kinds plus 18 planner-setting variants and a comparison with the last release.

## Slide 6: First wrong-result bug: range containment with NULL

This example is in our paper. The operator is strict, so for a NULL element the answer must be NULL. Released 17 and 18.6 and master print true because a planner support function folds it to a constant. No crash, no error. Our scalar-subquery rewrite disagreed with the original within the first 150 test cases. Root cause is in rangetypes.c; we sent a patch for 17, 18 and master.

## Slide 7: Everything we found upstream

The table lists all nine reports. All were found by the project's tooling and reproduced; reproducers and patches are in docs/bughunt in the repository. Four have been answered by PostgreSQL developers: the MERGE bug and the parallel Append assertion are confirmed, the parallel Append bug is already fixed on master, and the to_char fix is committed. The rest are waiting for replies.

## Slide 8: The other bugs in a few words

JSON_TABLE: it never assigns collations to its context item and PASSING arguments; the grammar campaign tripped an assertion in execExpr.c and 18.6 gives a silent wrong result. NOT IN: a regression from commit 383eb21ebf, present in 19rc1 and master but not 18.6. IGNORE NULLS: a frame scan that can hang. dependencies.c: an assertion when an extended statistic has a duplicate expression. The MCV bug: pg_restore_extended_stats accepts non-finite frequencies.

## Slide 9: Deep dives

Three slides about #19802 (MERGE), #19803 (parallel Append assertion) and #19771 (to_char NaN), presented by the teammate who worked on them. Insert them after this slide.

## Slide 10: Triage: reproduce, shrink, localize

Every candidate is reproduced three times on a fresh connection, then reduced: first on the derivation tree, then on tokens. For the JSON_TABLE case this took 590 tokens down to 79, where token reduction alone reached only 116. Localization runs the query under every plan variant: if one removes the problem, the bug is in that code path; if none does, it is an always-applied rewrite or constant folding. The output includes a draft report.

## Slide 11: Precision: strong oracles also raise false alarms

Claim two: we measure soundness. 93 candidates: 7 new real bugs, 15 real bugs that were also reported upstream by others, 37 false positives, 28 flaky, 6 still to verify. Precision is 0.16 without the duplicates and 0.37 if they count. The false alarms came from ten classes, for example equal intervals printed differently and a collation-changing rewrite. All ten are fixed with tests. Four appeared only in the long campaigns and were fixed afterwards, so the improved precision is not yet a campaign measurement.

## Slide 12: The LLM extension and its gate

Claim three. We mine PostgreSQL commits that touch the planner, executor or parser. The LLM gets a digest and returns grammar alternatives, seed queries and equivalence rewrites. A gate checks that the fragment parses, is actually used, that at least 60% of statements run on the server, that seeds run, and that more of the commit's changed lines are covered. Failures return to the model for up to three repair rounds. The model used was Gemini Flash on the free tier; 10 of 25 mined commits were used because of the daily quota. Four were accepted.

## Slide 13: Ground truth: 23 real bugs put back

We took every suitable PostgreSQL fix between 31 July and 16 October that had a regression test, 23 in all, and reverted them. We build a fixed server, a solo server per bug, and an injected server with all 23. A finding counts for a bug if it fails on that bug's solo server and passes on the fixed one. 20 of the 23 change what a query returns; only 9 of those would be visible to a crash-only fuzzer, which is the argument for oracles.

## Slide 14: Results: reach of the typed grammar

Random mutation runs fifteen times more test cases, yet reaches only 22 percent of backend lines against 37 for the grammar, because only 26 percent of its statements are valid. The oracles do not add lines but roughly double the number of distinct plan shapes. The LLM adds SQL features but no coverage. With five trials the smallest possible p value is 0.008, so we also report effect sizes.

## Slide 15: Results: re-injected bugs

The best arm found 2 of 20 bugs. The internal error dfcf6fa7 is found by all grammar arms in nearly every trial and never by random. The assertion 11b56ee2 was found once by the oracle and LLM arms. No arm found any of the 8 wrong-result bugs in one hour. So this benchmark does not show an oracle advantage; the evidence for oracles is that they found real wrong results in released PostgreSQL. One hour and five trials are short for bugs that need specific feature combinations.

## Slide 16: What the numbers tell us

First, typing pays off for reach. Second, oracles find the bugs users cannot see, but they cost precision, and precision is the limiting factor, not generator power. Third, an LLM that must not be wrong needs a server-side gate, and even then one rewrite slipped through.

## Slide 17: What went wrong and how we handled it

A worker's server failed crash recovery after an assertion, so 14 trials were re-run with the same seeds. A laptop went to sleep, but trial clocks are monotonic so the budget is unchanged. The LLM was Gemini Flash on the free tier. Four false-alarm classes appeared in the campaigns and were fixed afterwards; we did not re-run the campaigns. We ran 5 trials per arm instead of 10.

## Slide 18: Next steps to 13 November

Verify the six open candidates and re-run the earlier reproducers, follow the upstream threads, then write the paper. Questions for the professor: do committer-confirmed bugs, one already fixed, meet the top band even though the benchmark shows no oracle advantage; and is it acceptable to argue the post-fix precision from stored reproducers.

## Slide 19: Thank you

Repository link on the slide. All reproducers, patches, run data and the triage ledger are in the repository.

