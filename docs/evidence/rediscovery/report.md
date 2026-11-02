# Evaluation report: `rediscover_g3`

Trials per configuration: Grammar+Oracles = 1
Budget per trial: {"seconds": 150.0, "testcases": null}
Stop reasons: budget_seconds

## Median (IQR) per configuration

| Metric | Grammar+Oracles |
|---|---:|
| SQL features | 104 (104-104) |
| SQL feature coverage | 70.3% (70.3%-70.3%) |
| Feature pairs | 2,299 (2,299-2,299) |
| Distinct query shapes | 2,282 (2,282-2,282) |
| Distinct plan shapes | 979 (979-979) |
| Metamorphic checks run | 966 (966-966) |
| Plan-variant runs | 3,914 (3,914-3,914) |
| Parse-valid rate | 100.0% (100.0%-100.0%) |
| Valid-query rate | 98.7% (98.7%-98.7%) |
| Statements/s | 33.6 (33.6-33.6) |
| Test cases | 1,727 (1,727-1,727) |
| Unique bug candidates | 9 (9-9) |
| Known bugs reproduced | 9 (9-9) |
| Time to first bug (s) | 9.3 (9.3-9.3) |

## Median with 95% bootstrap confidence interval

| Metric | Grammar+Oracles |
|---|---:|
| SQL features | 104 [104, 104] |
| SQL feature coverage | 70.3% [70.3%, 70.3%] |
| Feature pairs | 2,299 [2,299, 2,299] |
| Distinct query shapes | 2,282 [2,282, 2,282] |
| Distinct plan shapes | 979 [979, 979] |
| Metamorphic checks run | 966 [966, 966] |
| Plan-variant runs | 3,914 [3,914, 3,914] |
| Parse-valid rate | 100.0% [100.0%, 100.0%] |
| Valid-query rate | 98.7% [98.7%, 98.7%] |
| Statements/s | 33.6 [33.6, 33.6] |
| Test cases | 1,727 [1,727, 1,727] |
| Unique bug candidates | 9 [9, 9] |
| Known bugs reproduced | 9 [9, 9] |
| Time to first bug (s) | 9.3 [9.3, 9.3] |

## Unique bug candidates

| Signature | Outcome | Strength | SQLSTATE | Message | Found by (trials) | Known bug |
|---|---|---|---|---|---|---|
| `2ea521cc40ad` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles (1) | pgbug-19771 |
| `2fafe019f451` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles (1) | c-01 |
| `3dc78dd95f41` | internal_error | message | XX000 | SubPlan found with no parent plan | Grammar+Oracles (1) | pgbug-19802 |
| `68e520951660` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles (1) | pgbug-19768 |
| `760019308833` | wrong_result | diff | - | metamorphic check tlp_where failed: 1 rows vs 2 rows | Grammar+Oracles (1) | audit-f1 |
| `787ac79a1b25` | performance | message | - | row estimate rises when the WHERE clause is added: 1000.0 -> 1e+100 | Grammar+Oracles (1) | esi-nonfinite |
| `81f21381e461` | hang | message | - | statement ignored statement_timeout and cancel for 10 s; server restarted | Grammar+Oracles (1) | audit-f2 |
| `8a4e039bb76f` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles (1) | pgbug-19803 |
| `dadb554fcc93` | wrong_result | diff | - | metamorphic check expr:scalar_sub failed: 2 rows vs 2 rows | Grammar+Oracles (1) | pgbug-19793 |

Each signature has a replayable `testcase.sql` under `<config>/trial-NN/failures/<signature>/`. Validate on a fresh server before reporting.
