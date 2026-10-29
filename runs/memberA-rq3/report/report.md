# Evaluation report: `rq3`

Trials per configuration: Grammar+Oracles+LLM = 5, Grammar = 5, Grammar+Oracles = 5, Random/Mutation = 5
Budget per trial: {"seconds": 3600.0, "testcases": null}
Stop reasons: budget_seconds

## Median (IQR) per configuration

| Metric | Grammar+Oracles+LLM | Grammar | Grammar+Oracles | Random/Mutation |
|---|---:|---:|---:|---:|
| SQL features | 106 (106-106) | 101 (101-101) | 101 (101-101) | 19 (19-20) |
| SQL feature coverage | 71.6% (71.6%-71.6%) | 68.2% (68.2%-68.2%) | 68.2% (68.2%-68.2%) | 12.8% (12.8%-13.5%) |
| Feature pairs | 2,431 (2,430-2,446) | 2,512 (2,509-2,514) | 2,458 (2,447-2,470) | 45 (41-45) |
| Distinct query shapes | 27,075 (26,476-27,526) | 43,993 (37,079-45,877) | 47,002 (44,676-47,786) | 3,205 (3,165-3,224) |
| Distinct plan shapes | 13,795 (12,922-14,855) | 11,465 (9,840-11,823) | 19,487 (18,915-20,779) | 21 (19-22) |
| Metamorphic checks run | 15,717 (15,674-16,432) | - | 26,558 (26,113-26,814) | - |
| Plan-variant runs | 63,744 (63,322-66,908) | 53,860 (47,806-55,680) | 105,888 (102,962-107,080) | 31,948 (30,968-33,390) |
| Parse-valid rate | 99.9% (99.9%-99.9%) | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) | 33.6% (33.6%-33.7%) |
| Valid-query rate | 95.2% (95.1%-95.4%) | 99.5% (99.3%-99.6%) | 99.7% (99.6%-99.8%) | 26.0% (25.9%-26.0%) |
| Statements/s | 17.2 (16.9-17.9) | 36.4 (30.5-37.1) | 26.8 (25.5-29.4) | 62.0 (60.5-64.3) |
| Test cases | 24,271 (24,093-25,256) | 38,674 (32,079-39,929) | 38,073 (36,622-39,140) | 223,101 (217,745-231,508) |
| Unique bug candidates | 1 (1-2) | 7 (1-7) | 2 (1-2) | 0 (0-0) |
| Known bugs reproduced | 2 (2-2) | 2 (2-2) | 2 (2-2) | 0 (0-0) |
| Time to first bug (s) | 1,108.6 (764.4-1,328.7) | 457.6 (303.4-498.9) | 249.3 (239.7-767.9) | 409.2 (409.2-409.2) |

## Median with 95% bootstrap confidence interval

| Metric | Grammar+Oracles+LLM | Grammar | Grammar+Oracles | Random/Mutation |
|---|---:|---:|---:|---:|
| SQL features | 106 [106, 106] | 101 [101, 101] | 101 [101, 101] | 19 [19, 21] |
| SQL feature coverage | 71.6% [71.6%, 71.6%] | 68.2% [68.2%, 68.2%] | 68.2% [68.2%, 68.2%] | 12.8% [12.8%, 14.2%] |
| Feature pairs | 2,431 [2,414, 2,459] | 2,512 [2,506, 2,514] | 2,458 [2,446, 2,477] | 45 [40, 48] |
| Distinct query shapes | 27,075 [25,171, 54,779] | 43,993 [31,784, 46,612] | 47,002 [36,837, 48,913] | 3,205 [2,716, 3,243] |
| Distinct plan shapes | 13,795 [12,884, 24,146] | 11,465 [8,494, 11,892] | 19,487 [16,576, 24,399] | 21 [17, 24] |
| Metamorphic checks run | 15,717 [14,743, 32,200] | - | 26,558 [21,268, 30,484] | - |
| Plan-variant runs | 63,744 [59,788, 129,548] | 53,860 [37,242, 58,276] | 105,888 [84,996, 121,752] | 31,948 [25,944, 33,544] |
| Parse-valid rate | 99.9% [99.8%, 99.9%] | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 33.6% [33.5%, 33.7%] |
| Valid-query rate | 95.2% [93.3%, 96.4%] | 99.5% [99.1%, 99.7%] | 99.7% [99.4%, 99.8%] | 26.0% [25.9%, 26.1%] |
| Statements/s | 17.2 [16.3, 31.9] | 36.4 [26.2, 37.5] | 26.8 [21.6, 31.5] | 62.0 [50.4, 65.6] |
| Test cases | 24,271 [22,585, 48,050] | 38,674 [27,351, 40,534] | 38,073 [31,066, 43,462] | 223,101 [181,563, 236,317] |
| Unique bug candidates | 1 [1, 5] | 7 [1, 15] | 2 [1, 3] | 0 [0, 6] |
| Known bugs reproduced | 2 [2, 3] | 2 [2, 2] | 2 [0, 3] | 0 [0, 0] |
| Time to first bug (s) | 1,108.6 [264.4, 2,308.0] | 457.6 [202.5, 3,087.3] | 249.3 [228.4, 2,711.9] | 409.2 [409.2, 409.2] |

## Pairwise comparisons

`A12` is the probability that B beats A on that metric (0.5 = no difference; lower-is-better metrics are flipped). `p` is from a two-sided Mann-Whitney U test.

| A | B | Metric | Median A | Median B | p | A12 | Effect |
|---|---|---|---:|---:|---:|---:|---|
| Grammar+Oracles+LLM | Grammar | SQL features | 106 | 101 | 0.004 | 0.00 | large |
| Grammar+Oracles+LLM | Grammar | SQL feature coverage | 71.6% | 68.2% | 0.004 | 0.00 | large |
| Grammar+Oracles+LLM | Grammar | Feature pairs | 2,431 | 2,512 | 0.012 | 1.00 | large |
| Grammar+Oracles+LLM | Grammar | Distinct query shapes | 27,075 | 43,993 | 0.151 | 0.80 | large |
| Grammar+Oracles+LLM | Grammar | Distinct plan shapes | 13,795 | 11,465 | 0.008 | 0.00 | large |
| Grammar+Oracles+LLM | Grammar | Plan-variant runs | 63,744 | 53,860 | 0.008 | 0.00 | large |
| Grammar+Oracles+LLM | Grammar | Parse-valid rate | 99.9% | 100.0% | 0.007 | 1.00 | large |
| Grammar+Oracles+LLM | Grammar | Valid-query rate | 95.2% | 99.5% | 0.008 | 1.00 | large |
| Grammar+Oracles+LLM | Grammar | Statements/s | 17.2 | 36.4 | 0.032 | 0.92 | large |
| Grammar+Oracles+LLM | Grammar | Test cases | 24,271 | 38,674 | 0.151 | 0.80 | large |
| Grammar+Oracles+LLM | Grammar | Unique bug candidates | 1 | 7 | 0.264 | 0.72 | large |
| Grammar+Oracles+LLM | Grammar | Known bugs reproduced | 2 | 2 | 0.424 | 0.40 | small |
| Grammar+Oracles+LLM | Grammar | Time to first bug (s) | 1,108.6 | 457.6 | 0.421 | 0.68 | medium |
| Grammar | Grammar+Oracles | SQL features | 101 | 101 | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | SQL feature coverage | 68.2% | 68.2% | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Feature pairs | 2,512 | 2,458 | 0.012 | 0.00 | large |
| Grammar | Grammar+Oracles | Distinct query shapes | 43,993 | 47,002 | 0.222 | 0.76 | large |
| Grammar | Grammar+Oracles | Distinct plan shapes | 11,465 | 19,487 | 0.008 | 1.00 | large |
| Grammar | Grammar+Oracles | Plan-variant runs | 53,860 | 105,888 | 0.008 | 1.00 | large |
| Grammar | Grammar+Oracles | Parse-valid rate | 100.0% | 100.0% | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Valid-query rate | 99.5% | 99.7% | 0.151 | 0.80 | large |
| Grammar | Grammar+Oracles | Statements/s | 36.4 | 26.8 | 0.095 | 0.16 | large |
| Grammar | Grammar+Oracles | Test cases | 38,674 | 38,073 | 1.000 | 0.52 | negligible |
| Grammar | Grammar+Oracles | Unique bug candidates | 7 | 2 | 0.386 | 0.32 | medium |
| Grammar | Grammar+Oracles | Known bugs reproduced | 2 | 2 | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Time to first bug (s) | 457.6 | 249.3 | 0.841 | 0.56 | small |
| Grammar+Oracles | Random/Mutation | SQL features | 101 | 19 | 0.007 | 0.00 | large |
| Grammar+Oracles | Random/Mutation | SQL feature coverage | 68.2% | 12.8% | 0.007 | 0.00 | large |
| Grammar+Oracles | Random/Mutation | Feature pairs | 2,458 | 45 | 0.012 | 0.00 | large |
| Grammar+Oracles | Random/Mutation | Distinct query shapes | 47,002 | 3,205 | 0.008 | 0.00 | large |
| Grammar+Oracles | Random/Mutation | Distinct plan shapes | 19,487 | 21 | 0.008 | 0.00 | large |
| Grammar+Oracles | Random/Mutation | Plan-variant runs | 105,888 | 31,948 | 0.008 | 0.00 | large |
| Grammar+Oracles | Random/Mutation | Parse-valid rate | 100.0% | 33.6% | 0.007 | 0.00 | large |
| Grammar+Oracles | Random/Mutation | Valid-query rate | 99.7% | 26.0% | 0.008 | 0.00 | large |
| Grammar+Oracles | Random/Mutation | Statements/s | 26.8 | 62.0 | 0.008 | 1.00 | large |
| Grammar+Oracles | Random/Mutation | Test cases | 38,073 | 223,101 | 0.008 | 1.00 | large |
| Grammar+Oracles | Random/Mutation | Unique bug candidates | 2 | 0 | 0.129 | 0.20 | large |
| Grammar+Oracles | Random/Mutation | Known bugs reproduced | 2 | 0 | 0.023 | 0.10 | large |
| Grammar+Oracles | Random/Mutation | Time to first bug (s) | 249.3 | 409.2 | 1.000 | 0.40 | small |
| Random/Mutation | Grammar+Oracles+LLM | SQL features | 19 | 106 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | SQL feature coverage | 12.8% | 71.6% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Feature pairs | 45 | 2,431 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Distinct query shapes | 3,205 | 27,075 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Distinct plan shapes | 21 | 13,795 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Plan-variant runs | 31,948 | 63,744 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Parse-valid rate | 33.6% | 99.9% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Valid-query rate | 26.0% | 95.2% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Statements/s | 62.0 | 17.2 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Test cases | 223,101 | 24,271 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Unique bug candidates | 0 | 1 | 0.126 | 0.80 | large |
| Random/Mutation | Grammar+Oracles+LLM | Known bugs reproduced | 0 | 2 | 0.006 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Time to first bug (s) | 409.2 | 1,108.6 | 0.667 | 0.20 | large |
| Random/Mutation | Grammar | SQL features | 19 | 101 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar | SQL feature coverage | 12.8% | 68.2% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar | Feature pairs | 45 | 2,512 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar | Distinct query shapes | 3,205 | 43,993 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar | Distinct plan shapes | 21 | 11,465 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar | Plan-variant runs | 31,948 | 53,860 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar | Parse-valid rate | 33.6% | 100.0% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar | Valid-query rate | 26.0% | 99.5% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar | Statements/s | 62.0 | 36.4 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar | Test cases | 223,101 | 38,674 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar | Unique bug candidates | 0 | 7 | 0.030 | 0.92 | large |
| Random/Mutation | Grammar | Known bugs reproduced | 0 | 2 | 0.004 | 1.00 | large |
| Random/Mutation | Grammar | Time to first bug (s) | 409.2 | 457.6 | 1.000 | 0.40 | small |
| Random/Mutation | Grammar+Oracles | SQL features | 19 | 101 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | SQL feature coverage | 12.8% | 68.2% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Feature pairs | 45 | 2,458 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Distinct query shapes | 3,205 | 47,002 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Distinct plan shapes | 21 | 19,487 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Plan-variant runs | 31,948 | 105,888 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Parse-valid rate | 33.6% | 100.0% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Valid-query rate | 26.0% | 99.7% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Statements/s | 62.0 | 26.8 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles | Test cases | 223,101 | 38,073 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles | Unique bug candidates | 0 | 2 | 0.129 | 0.80 | large |
| Random/Mutation | Grammar+Oracles | Known bugs reproduced | 0 | 2 | 0.023 | 0.90 | large |
| Random/Mutation | Grammar+Oracles | Time to first bug (s) | 409.2 | 249.3 | 1.000 | 0.60 | small |

## Unique bug candidates

| Signature | Outcome | Strength | SQLSTATE | Message | Found by (trials) | Known bug |
|---|---|---|---|---|---|---|
| `4fedb431a765` | internal_error | message | XX000 | could not find pathkey item to sort | Grammar (5), Grammar+Oracles+LLM (5), Grammar+Oracles (4) | rb-8b29b8da,rb-dfcf6fa7 |
| `cde9712bc8db` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (1), Grammar+Oracles+LLM (1), Grammar+Oracles (1) | - |
| `1a3d32e70e0c` | wrong_result | diff | - | result differs under plan variant xversion: 218 rows by default, 211 rows with variant | Grammar (1) | - |
| `1d6e4fd4cf5b` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 1 rows with variant | Grammar (1) | - |
| `22f5c7294dc6` | wrong_result | diff | - | result differs under plan variant xversion: 218 rows by default, 211 rows with variant | Grammar (1) | - |
| `23e696368d4a` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 2 rows with variant | Grammar (1) | - |
| `275e49476af8` | wrong_result | diff | - | result differs under plan variant mergejoin_only: 146 rows by default, 146 rows with variant | Grammar (1) | - |
| `28a639c0f92c` | wrong_result | diff | - | result differs under plan variant xversion: 218 rows by default, 211 rows with variant | Grammar (1) | - |
| `3f83ff1c49e0` | wrong_result | diff | - | result differs under plan variant xversion: 218 rows by default, 211 rows with variant | Grammar (1) | - |
| `448f485d72d5` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles (1) | rb-11b56ee2 |
| `4dd0f9bd9afc` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 222 rows with variant | Grammar (1) | - |
| `53f867a5bcc8` | wrong_result | diff | - | result differs under plan variant xversion: 2 rows by default, 1 rows with variant | Random/Mutation (1) | - |
| `64f173382883` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 202 rows with variant | Grammar (1) | - |
| `65cd1cb9b0bf` | performance | message | - | row estimate rises when the WHERE clause is added: 300.0 -> 720.0 | Grammar+Oracles (1) | - |
| `686d5e233140` | wrong_result | diff | - | result differs under plan variant xversion: 30 rows by default, 30 rows with variant | Random/Mutation (1) | - |
| `68e520951660` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (1) | - |
| `7ca8a780a4bc` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 2 rows with variant | Grammar (1) | - |
| `7cad44367934` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 2 rows with variant | Grammar (1) | - |
| `83bdce4a0403` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles+LLM (1) | rb-11b56ee2 |
| `886c0db769c0` | wrong_result | diff | - | result differs under plan variant xversion: 378 rows by default, 189 rows with variant | Random/Mutation (1) | - |
| `8a0e13634ebf` | wrong_result | diff | - | result differs under plan variant no_self_join_elim: 101 rows by default, 101 rows with variant | Grammar (1) | - |
| `90ecfa669ba3` | wrong_result | diff | - | metamorphic check tlp_where failed: 1 rows vs 1 rows | Grammar+Oracles+LLM (1) | - |
| `a819a7520c99` | wrong_result | diff | - | metamorphic check expr:llm_nullif_null_reduction failed: 46 rows vs 46 rows | Grammar+Oracles+LLM (1) | - |
| `b0171fcfb39a` | wrong_result | diff | - | result differs under plan variant index_scans: 0 rows by default, 1 rows with variant | Random/Mutation (1) | - |
| `ba7274037f5f` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 1 rows with variant | Grammar (1) | - |
| `c51c4dacc7f1` | internal_error | message | XX000 | no relation entry for relid 1 | Grammar (1) | - |
| `c7cb42ade92c` | wrong_result | diff | - | result differs under plan variant xversion: 218 rows by default, 211 rows with variant | Grammar (1) | - |
| `cc7181e74014` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (1) | - |
| `d1f574d66122` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 1 rows with variant | Grammar (1) | - |
| `d9d8b441903e` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 1 rows with variant | Grammar (1) | - |
| `db02c93fef27` | wrong_result | diff | - | metamorphic check tlp_where failed: 1 rows vs 1 rows | Grammar+Oracles+LLM (1) | - |
| `dc18174656f6` | wrong_result | diff | - | result differs under plan variant no_self_join_elim: 101 rows by default, 101 rows with variant | Grammar (1) | - |
| `dd35fab1c86e` | wrong_result | diff | - | result differs under plan variant xversion: 168 rows by default, 166 rows with variant | Grammar (1) | - |
| `de1cf51162c1` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 1 rows with variant | Grammar (1) | - |
| `ec8b42ef87ac` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles (1) | - |
| `ecf5c8cfe1e4` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 1 rows with variant | Grammar (1) | - |
| `efa9efb8acc1` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles (1) | - |
| `f03cf100a032` | wrong_result | diff | - | result differs under plan variant no_eager_agg: 0 rows by default, 80 rows with variant | Random/Mutation (1) | - |
| `f6f5012e736d` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (1) | - |
| `f7f40a5ab8df` | wrong_result | diff | - | result differs under plan variant xversion: 0 rows by default, 1 rows with variant | Grammar (1) | - |
| `f8f3de89048d` | wrong_result | diff | - | result differs under plan variant xversion: 19 rows by default, 19 rows with variant | Random/Mutation (1) | - |

Each signature has a replayable `testcase.sql` under `<config>/trial-NN/failures/<signature>/`. Validate on a fresh server before reporting.

## Re-injected bugs (RQ3)

Trials in which the arm found the bug, and the median time to the first finding (failures attributed by replay on single-bug servers, `pgfuzz bench attribute`).

| Bug | Symptom | Grammar+Oracles+LLM | Grammar | Grammar+Oracles | Random/Mutation |
|---|---|---:|---:|---:|---:|
| rb-11b56ee2 | assertion | 1/5 (1858 s) | 0/5 | 1/5 (2901 s) | 0/5 |
| rb-94e1385e | wrong_result | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-41180127 | missing_error | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-b28a2b2b | wrong_result | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-d8444163 | wrong_result | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-62e46c00 | error | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-738d19d4 | internal_error | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-6b858a36 | assertion | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-8b29b8da | internal_error | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-d764d61a | wrong_result | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-dfcf6fa7 | internal_error | 5/5 (1109 s) | 5/5 (458 s) | 4/5 (509 s) | 0/5 |
| rb-a464d31f | assertion | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-852fd5b8 | internal_error | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-a8bb1a77 | assertion | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-35d3f206 | internal_error | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-1bf74c80 | wrong_result | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-7774249d | wrong_result | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-0d995793 | wrong_result | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-d6eac691 | wrong_result | 0/5 | 0/5 | 0/5 | 0/5 |
| rb-3b120b1e | missing_error | 0/5 | 0/5 | 0/5 | 0/5 |
| **bugs found** | | **2/20** | **1/20** | **2/20** | **0/20** |

Failures that also reproduce on the fixed server (native): 20; not attributable to one injected bug: 20.
