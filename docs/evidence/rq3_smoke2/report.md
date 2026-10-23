# Evaluation report: `rq3_smoke2`

Trials per configuration: Random/Mutation = 1, Grammar = 1, Grammar+Oracles = 1, Grammar+Oracles+LLM = 1
Budget per trial: {"seconds": 900.0, "testcases": null}
Stop reasons: budget_seconds

## Median (IQR) per configuration

| Metric | Random/Mutation | Grammar | Grammar+Oracles | Grammar+Oracles+LLM |
|---|---:|---:|---:|---:|
| SQL features | 17 (17-17) | 101 (101-101) | 101 (101-101) | 101 (101-101) |
| SQL feature coverage | 11.5% (11.5%-11.5%) | 68.2% (68.2%-68.2%) | 68.2% (68.2%-68.2%) | 68.2% (68.2%-68.2%) |
| Feature pairs | 39 (39-39) | 2,505 (2,505-2,505) | 2,491 (2,491-2,491) | 2,491 (2,491-2,491) |
| Distinct query shapes | 2,686 (2,686-2,686) | 19,810 (19,810-19,810) | 19,050 (19,050-19,050) | 18,972 (18,972-18,972) |
| Distinct plan shapes | 22 (22-22) | 5,416 (5,416-5,416) | 5,968 (5,968-5,968) | 5,937 (5,937-5,937) |
| Metamorphic checks run | - | - | 7,532 (7,532-7,532) | 7,499 (7,499-7,499) |
| Plan-variant runs | 25,372 (25,372-25,372) | 24,014 (24,014-24,014) | 30,250 (30,250-30,250) | 30,112 (30,112-30,112) |
| Parse-valid rate | 33.8% (33.8%-33.8%) | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) |
| Valid-query rate | 26.3% (26.3%-26.3%) | 99.6% (99.6%-99.6%) | 99.7% (99.7%-99.7%) | 99.7% (99.7%-99.7%) |
| Statements/s | 193.4 (193.4-193.4) | 62.5 (62.5-62.5) | 47.6 (47.6-47.6) | 47.4 (47.4-47.4) |
| Test cases | 174,104 (174,104-174,104) | 16,841 (16,841-16,841) | 15,861 (15,861-15,861) | 15,800 (15,800-15,800) |
| Unique bug candidates | 2 (2-2) | 2 (2-2) | 1 (1-1) | 1 (1-1) |
| Known bugs reproduced | 1 (1-1) | 0 (0-0) | 2 (2-2) | 2 (2-2) |
| Time to first bug (s) | 134.1 (134.1-134.1) | 676.8 (676.8-676.8) | 158.5 (158.5-158.5) | 160.2 (160.2-160.2) |

## Pairwise comparisons

`A12` is the probability that B beats A on that metric (0.5 = no difference; lower-is-better metrics are flipped). `p` is from a two-sided Mann-Whitney U test.

| A | B | Metric | Median A | Median B | p | A12 | Effect |
|---|---|---|---:|---:|---:|---:|---|
| Random/Mutation | Grammar | SQL features | 17 | 101 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar | SQL feature coverage | 11.5% | 68.2% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar | Feature pairs | 39 | 2,505 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar | Distinct query shapes | 2,686 | 19,810 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar | Distinct plan shapes | 22 | 5,416 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar | Plan-variant runs | 25,372 | 24,014 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar | Parse-valid rate | 33.8% | 100.0% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar | Valid-query rate | 26.3% | 99.6% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar | Statements/s | 193.4 | 62.5 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar | Test cases | 174,104 | 16,841 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar | Unique bug candidates | 2 | 2 | 1.000 | 0.50 | negligible |
| Random/Mutation | Grammar | Known bugs reproduced | 1 | 0 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar | Time to first bug (s) | 134.1 | 676.8 | 1.000 | 0.00 | large |
| Grammar | Grammar+Oracles | SQL features | 101 | 101 | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | SQL feature coverage | 68.2% | 68.2% | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Feature pairs | 2,505 | 2,491 | 1.000 | 0.00 | large |
| Grammar | Grammar+Oracles | Distinct query shapes | 19,810 | 19,050 | 1.000 | 0.00 | large |
| Grammar | Grammar+Oracles | Distinct plan shapes | 5,416 | 5,968 | 1.000 | 1.00 | large |
| Grammar | Grammar+Oracles | Plan-variant runs | 24,014 | 30,250 | 1.000 | 1.00 | large |
| Grammar | Grammar+Oracles | Parse-valid rate | 100.0% | 100.0% | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Valid-query rate | 99.6% | 99.7% | 1.000 | 1.00 | large |
| Grammar | Grammar+Oracles | Statements/s | 62.5 | 47.6 | 1.000 | 0.00 | large |
| Grammar | Grammar+Oracles | Test cases | 16,841 | 15,861 | 1.000 | 0.00 | large |
| Grammar | Grammar+Oracles | Unique bug candidates | 2 | 1 | 1.000 | 0.00 | large |
| Grammar | Grammar+Oracles | Known bugs reproduced | 0 | 2 | 1.000 | 1.00 | large |
| Grammar | Grammar+Oracles | Time to first bug (s) | 676.8 | 158.5 | 1.000 | 1.00 | large |
| Grammar+Oracles | Grammar+Oracles+LLM | SQL features | 101 | 101 | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles+LLM | SQL feature coverage | 68.2% | 68.2% | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles+LLM | Feature pairs | 2,491 | 2,491 | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles+LLM | Distinct query shapes | 19,050 | 18,972 | 1.000 | 0.00 | large |
| Grammar+Oracles | Grammar+Oracles+LLM | Distinct plan shapes | 5,968 | 5,937 | 1.000 | 0.00 | large |
| Grammar+Oracles | Grammar+Oracles+LLM | Metamorphic checks run | 7,532 | 7,499 | 1.000 | 0.00 | large |
| Grammar+Oracles | Grammar+Oracles+LLM | Plan-variant runs | 30,250 | 30,112 | 1.000 | 0.00 | large |
| Grammar+Oracles | Grammar+Oracles+LLM | Parse-valid rate | 100.0% | 100.0% | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles+LLM | Valid-query rate | 99.7% | 99.7% | 1.000 | 0.00 | large |
| Grammar+Oracles | Grammar+Oracles+LLM | Statements/s | 47.6 | 47.4 | 1.000 | 0.00 | large |
| Grammar+Oracles | Grammar+Oracles+LLM | Test cases | 15,861 | 15,800 | 1.000 | 0.00 | large |
| Grammar+Oracles | Grammar+Oracles+LLM | Unique bug candidates | 1 | 1 | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles+LLM | Known bugs reproduced | 2 | 2 | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles+LLM | Time to first bug (s) | 158.5 | 160.2 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar+Oracles | SQL features | 17 | 101 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | SQL feature coverage | 11.5% | 68.2% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Feature pairs | 39 | 2,491 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Distinct query shapes | 2,686 | 19,050 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Distinct plan shapes | 22 | 5,968 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Plan-variant runs | 25,372 | 30,250 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Parse-valid rate | 33.8% | 100.0% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Valid-query rate | 26.3% | 99.7% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Statements/s | 193.4 | 47.6 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar+Oracles | Test cases | 174,104 | 15,861 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar+Oracles | Unique bug candidates | 2 | 1 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar+Oracles | Known bugs reproduced | 1 | 2 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Time to first bug (s) | 134.1 | 158.5 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | SQL features | 17 | 101 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | SQL feature coverage | 11.5% | 68.2% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Feature pairs | 39 | 2,491 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Distinct query shapes | 2,686 | 18,972 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Distinct plan shapes | 22 | 5,937 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Plan-variant runs | 25,372 | 30,112 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Parse-valid rate | 33.8% | 100.0% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Valid-query rate | 26.3% | 99.7% | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Statements/s | 193.4 | 47.4 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Test cases | 174,104 | 15,800 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Unique bug candidates | 2 | 1 | 1.000 | 0.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Known bugs reproduced | 1 | 2 | 1.000 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Time to first bug (s) | 134.1 | 160.2 | 1.000 | 0.00 | large |

## Unique bug candidates

| Signature | Outcome | Strength | SQLSTATE | Message | Found by (trials) | Known bug |
|---|---|---|---|---|---|---|
| `4fedb431a765` | internal_error | message | XX000 | could not find pathkey item to sort | Grammar+Oracles+LLM (1), Grammar+Oracles (1) | rb-8b29b8da,rb-dfcf6fa7 |
| `256dc4599fec` | wrong_result | diff | - | result differs under plan variant xversion: 6400 rows by default, 6400 rows with variant | Grammar (1) | - |
| `5f795c1e0a66` | internal_error | message | XX000 | Append child's targetlist doesn't match Append | Grammar (1) | - |
| `6efd24cf879b` | assertion | stack | 42601 | syntax error at or near "*" | Random/Mutation (1) | rb-a8bb1a77 |
| `ca37f4a4a5e1` | crash | message | 42601 | syntax error at or near "KrLAayL" | Random/Mutation (1) | - |

Each signature has a replayable `testcase.sql` under `<config>/trial-NN/failures/<signature>/`. Validate on a fresh server before reporting.

## Re-injected bugs (RQ3)

Trials in which the arm found the bug, and the median time to the first finding (failures attributed by replay on single-bug servers, `pgfuzz bench attribute`).

| Bug | Symptom | Random/Mutation | Grammar | Grammar+Oracles | Grammar+Oracles+LLM |
|---|---|---:|---:|---:|---:|
| rb-11b56ee2 | assertion | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-94e1385e | wrong_result | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-41180127 | missing_error | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-b28a2b2b | wrong_result | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-d8444163 | wrong_result | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-62e46c00 | error | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-738d19d4 | internal_error | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-6b858a36 | assertion | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-8b29b8da | internal_error | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-d764d61a | wrong_result | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-dfcf6fa7 | internal_error | 0/1 | 0/1 | 1/1 (158 s) | 1/1 (160 s) |
| rb-a464d31f | assertion | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-852fd5b8 | internal_error | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-a8bb1a77 | assertion | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-35d3f206 | internal_error | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-1bf74c80 | wrong_result | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-7774249d | wrong_result | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-0d995793 | wrong_result | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-d6eac691 | wrong_result | 0/1 | 0/1 | 0/1 | 0/1 |
| rb-3b120b1e | missing_error | 0/1 | 0/1 | 0/1 | 0/1 |
| **bugs found** | | **0/20** | **0/20** | **1/20** | **1/20** |

Failures that also reproduce on the fixed server (native): 1; not attributable to one injected bug: 3.
