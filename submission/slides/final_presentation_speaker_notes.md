# Speaker notes: final presentation

One section per slide; slide numbers match final_presentation.pptx.

## Slide 1: Title

Our project is a fuzzer for PostgreSQL that looks for wrong results, not only crashes. In one sentence: we generate SQL as typed trees, turn the trees into checks that know the right answer, and use an LLM to extend the generator from recent commits. It found nine bugs that we reported upstream; six are fixed, five of them with our patches.

## Slide 2: The problem: silent wrong results

This is a real bug our tool found, BUG #19793. The operator is strict, so for a NULL element the answer must be NULL. Released PostgreSQL 17 and 18 print true, because a planner support function folds the call to a constant. A crash fuzzer cannot see this. Of 23 recent PostgreSQL fixes we studied, 20 change what a query returns, and only 9 of those would show up as a crash or internal error.

## Slide 3: Our idea

Existing tools split into two camps. Grammar fuzzers like SQLsmith reach deep into the planner but only detect crashes. Oracle tools like SQLancer detect wrong results but use small generators of their own. Neither knows what changed in yesterday's commit. Our three claims connect them.

## Slide 4: How it works

The generator derives test cases from a typed grammar. Each query gets oracle checks attached as rewrites of its tree. The executor runs everything on an assertion-enabled PostgreSQL, under several planner settings and against the last release. Failures go to triage. Before a campaign, the LLM reads recent commits and proposes grammar additions, which a validation gate checks on the server.

## Slide 5: One tree, four jobs

Our grammar has 78 rules, 421 alternatives and 13 SQL types. Because each node is typed, replacing a node by another derivation of the same type keeps the query valid. The same tree serves four jobs: generation, mutation, rewriting by oracles, and reduction in triage. Feedback weights favour alternatives that reach new plans, and literals come from the data.

## Slide 6: Oracles that know the right answer

Ternary logic partitioning: every row makes a predicate true, false or NULL, exactly one. So a query must equal the union of its three partitions. We apply such rewrites to one node of the tree, so they also work inside subqueries. Plan variants run the query under 18 planner settings; the cross-version oracle compares with release 18.6. CERT checks row estimates, and the hang oracle catches statements that ignore the timeout.

## Slide 7: Triage: from failure to upstream report

A raw finding is a long query. Triage reduces it first on the derivation tree, then on tokens, and runs it under every plan variant: if a setting removes the problem, the bug is in that code path. The output is a small reproducer and a draft report in the format of the PostgreSQL bug form.

## Slide 8: The LLM extension and its gate

We mine commits that touch the planner, executor or parser. The LLM returns grammar alternatives, seed queries and equivalence rewrites. The gate checks that a fragment parses, is used, runs on the server at least 60% of the time, and covers more of the commit's changed lines. Failures go back for up to three repair rounds. We used Gemini Flash on the free tier.

## Slide 9: Evaluation

All arms share the server build, schema, oracles, budget and seeds; they differ only in the generator. RQ3 uses a benchmark we built: 23 real PostgreSQL bugs fixed between July and October 2026, put back into one server, with one server per bug to attribute findings. Statistics: medians, Mann-Whitney U and Vargha-Delaney A12; with 5 trials the smallest possible p is 0.008.

## Slide 10: RQ1: the typed grammar reaches much more

Only 26% of random statements are valid, so most of them never reach the planner. The grammar reaches 36.7% of backend lines against 22.2%, with A12 = 1.00. The oracles do not add lines, but roughly double the distinct plan shapes. The LLM adds SQL features, not coverage.

## Slide 11: RQ2: nine bugs reported upstream

Go through the table. Five came from the fuzzing campaigns, four from our targeted bug hunt on recent features. The oracles column shows that four of them are not crashes at all: they need a metamorphic or estimate oracle. A tenth bug, corr() under partial aggregation, is a new regression we found while deciding the last candidates; its report is ready to file.

## Slide 12: The tool finds every bug we reported

To check that the tool, and not only our manual work, recognises every reported bug, we added each reproducer as a seed that carries its own oracle, added the grammar features four of them need, and added a hang oracle. One 150-second trial then reported all nine, each matched to its catalogue entry, at unchanged validity. The fixed bugs reproduce on our base build, which predates the fixes.

## Slide 13: RQ2: precision is the bottleneck

Eight are new real bugs, fifteen are real bugs others reported first, forty-two are false positives, twenty-eight did not reproduce. Precision is 0.16, or 0.35 if duplicates count. The false positives come from eleven classes, all fixed with tests, for example equal intervals printed differently. The five classes found in the campaigns were fixed afterwards, so the improved precision is not yet a campaign measurement.

## Slide 14: RQ3: re-injected real bugs

We reverted 23 recent PostgreSQL fixes. 20 are observable. The best arm found 2 of 20 in one hour, and no arm found a wrong-result benchmark bug. The internal error dfcf6fa7 is found by every grammar arm almost every time, and never by random. So the benchmark does not show an advantage of the oracles; the evidence for the oracles is the real wrong results in RQ2.

## Slide 15: What we learned

First, typing pays: valid queries reach the planner. Second, oracles find bugs users cannot see, but a richer grammar also reaches the corners where two equivalent queries are not equivalent, so precision becomes the bottleneck. Third, an LLM is useful only behind a gate that tests its claims on the server, and even a tested rewrite is not a proven one.

## Slide 16: Limitations

Five trials per arm is few, so several conclusions rest on effect sizes. The false-positive fixes after the campaigns were not re-measured. The LLM was a free-tier model on ten commits. The rediscovery replays reproducers as seeds, so it shows the oracles recognise each bug, not that generation alone finds it in a short run. One system, one schema, one commit.

## Slide 17: Conclusion

We built a typed, tree-based fuzzer with oracles for wrong results and an LLM extension behind a server-side gate. It found nine PostgreSQL bugs that we reported; six are fixed upstream, five of them with our patches, one more is confirmed, and a tenth report is ready. Everything is in the repository: the tool, 151 unit tests, all run data, the triage ledger and every reproducer.

## Slide 18: Thank you

Everything is in the repository: tool, tests, run data, triage ledger, reproducers and patches.

