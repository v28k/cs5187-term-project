# Evaluation report: `rq1`

Trials per configuration: Random/Mutation = 5, Grammar = 5, Grammar+Oracles = 5, Grammar+Oracles, no bandit = 5, +LLM fragments = 5, +LLM seeds = 5, Grammar+Oracles+LLM = 5
Budget per trial: {"seconds": 3600.0, "testcases": null}
Stop reasons: budget_seconds

## Median (IQR) per configuration

| Metric | Random/Mutation | Grammar | Grammar+Oracles | Grammar+Oracles, no bandit | +LLM fragments | +LLM seeds | Grammar+Oracles+LLM |
|---|---:|---:|---:|---:|---:|---:|---:|
| Line coverage | 22.2% (21.9%-22.2%) | 36.7% (35.9%-36.7%) | 36.2% (36.1%-36.4%) | 36.2% (35.9%-36.4%) | 35.7% (35.7%-35.8%) | 35.6% (35.4%-35.8%) | 35.7% (35.6%-35.8%) |
| Branch coverage | 15.1% (15.0%-15.1%) | 27.1% (26.6%-27.2%) | 26.7% (26.6%-27.0%) | 26.8% (26.8%-26.9%) | 26.5% (26.4%-26.5%) | 26.4% (26.3%-26.5%) | 26.4% (26.4%-26.5%) |
| SQL features | 23 (22-24) | 101 (101-101) | 101 (101-101) | 101 (101-101) | 104 (104-104) | 106 (106-106) | 106 (106-106) |
| SQL feature coverage | 15.5% (14.9%-16.2%) | 68.2% (68.2%-68.2%) | 68.2% (68.2%-68.2%) | 68.2% (68.2%-68.2%) | 70.3% (70.3%-70.3%) | 71.6% (71.6%-71.6%) | 71.6% (71.6%-71.6%) |
| Feature pairs | 57 (57-58) | 2,517 (2,515-2,519) | 2,471 (2,462-2,472) | 2,517 (2,515-2,517) | 2,461 (2,450-2,471) | 2,484 (2,476-2,501) | 2,457 (2,439-2,473) |
| Distinct query shapes | 8,407 (7,701-8,885) | 80,477 (79,052-81,785) | 73,157 (57,767-77,330) | 75,216 (71,260-83,772) | 55,056 (49,914-58,934) | 75,506 (68,180-81,487) | 53,454 (50,402-72,506) |
| Distinct plan shapes | 43 (42-45) | 20,279 (20,049-21,354) | 34,313 (30,524-36,909) | 23,997 (21,187-24,869) | 25,972 (25,281-28,017) | 29,274 (28,875-36,256) | 26,375 (24,497-35,385) |
| Metamorphic checks run | - | - | 41,740 (36,348-45,612) | 31,491 (29,585-36,088) | 33,230 (28,932-34,763) | 42,488 (40,151-45,633) | 30,520 (30,273-41,184) |
| Plan-variant runs | 154,440 (134,264-173,100) | 105,372 (101,616-108,018) | 166,718 (145,956-182,410) | 125,192 (118,708-142,328) | 131,438 (115,686-137,914) | 171,456 (162,560-184,904) | 124,416 (122,648-165,884) |
| Parse-valid rate | 33.6% (33.6%-33.7%) | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) | 99.9% (99.8%-99.9%) | 100.0% (100.0%-100.0%) | 99.9% (99.9%-99.9%) |
| Valid-query rate | 26.0% (26.0%-26.0%) | 99.3% (82.6%-99.5%) | 96.3% (96.0%-96.6%) | 99.4% (99.3%-99.4%) | 95.5% (95.4%-96.1%) | 98.3% (98.3%-98.6%) | 95.3% (94.5%-95.7%) |
| Statements/s | 298.4 (260.6-335.8) | 67.2 (65.2-69.9) | 39.9 (38.3-43.8) | 45.0 (43.3-51.8) | 32.5 (29.3-33.6) | 42.8 (42.0-49.1) | 31.0 (30.3-43.3) |
| Test cases | 1,074,240 (938,252-1,209,074) | 71,228 (70,105-72,835) | 58,601 (53,593-66,738) | 64,923 (60,977-72,797) | 48,222 (41,687-50,046) | 63,655 (61,591-69,453) | 46,754 (45,779-62,292) |
| Unique bug candidates | 0 (0-0) | 1 (1-2) | 1 (1-3) | 1 (1-2) | 1 (0-2) | 3 (1-4) | 1 (0-2) |
| Known bugs reproduced | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) |
| Time to first bug (s) | - | 1,514.6 (1,090.7-2,027.7) | 1,956.4 (1,172.0-2,133.0) | 470.9 (211.7-2,184.9) | 280.0 (236.4-1,076.4) | 598.6 (373.7-740.9) | 953.9 (546.2-1,516.8) |

## Median with 95% bootstrap confidence interval

| Metric | Random/Mutation | Grammar | Grammar+Oracles | Grammar+Oracles, no bandit | +LLM fragments | +LLM seeds | Grammar+Oracles+LLM |
|---|---:|---:|---:|---:|---:|---:|---:|
| Line coverage | 22.2% [21.9%, 22.2%] | 36.7% [35.7%, 37.6%] | 36.2% [35.4%, 36.5%] | 36.2% [35.9%, 36.9%] | 35.7% [35.1%, 36.0%] | 35.6% [35.2%, 36.3%] | 35.7% [35.4%, 36.5%] |
| Branch coverage | 15.1% [14.8%, 15.1%] | 27.1% [26.5%, 27.6%] | 26.7% [26.4%, 27.1%] | 26.8% [26.5%, 27.4%] | 26.5% [26.1%, 26.7%] | 26.4% [25.8%, 26.9%] | 26.4% [26.2%, 26.9%] |
| SQL features | 23 [22, 24] | 101 [101, 101] | 101 [101, 101] | 101 [101, 101] | 104 [104, 104] | 106 [106, 106] | 106 [106, 106] |
| SQL feature coverage | 15.5% [14.9%, 16.2%] | 68.2% [68.2%, 68.2%] | 68.2% [68.2%, 68.2%] | 68.2% [68.2%, 68.2%] | 70.3% [70.3%, 70.3%] | 71.6% [71.6%, 71.6%] | 71.6% [71.6%, 71.6%] |
| Feature pairs | 57 [56, 62] | 2,517 [2,514, 2,521] | 2,471 [2,453, 2,479] | 2,517 [2,515, 2,518] | 2,461 [2,443, 2,484] | 2,484 [2,450, 2,503] | 2,457 [2,437, 2,499] |
| Distinct query shapes | 8,407 [7,367, 9,741] | 80,477 [63,512, 94,850] | 73,157 [41,267, 83,213] | 75,216 [66,285, 87,656] | 55,056 [43,092, 71,595] | 75,506 [60,048, 95,265] | 53,454 [50,384, 78,519] |
| Distinct plan shapes | 43 [35, 45] | 20,279 [16,296, 22,890] | 34,313 [19,631, 39,982] | 23,997 [19,934, 25,600] | 25,972 [20,618, 35,629] | 29,274 [25,940, 44,400] | 26,375 [23,501, 37,396] |
| Metamorphic checks run | - | - | 41,740 [23,167, 50,710] | 31,491 [28,343, 36,296] | 33,230 [24,599, 43,544] | 42,488 [32,727, 58,632] | 30,520 [28,395, 44,183] |
| Plan-variant runs | 154,440 [124,722, 195,960] | 105,372 [74,948, 121,920] | 166,718 [91,414, 202,114] | 125,192 [113,068, 145,364] | 131,438 [98,318, 173,298] | 171,456 [133,090, 238,068] | 124,416 [114,128, 178,474] |
| Parse-valid rate | 33.6% [33.6%, 33.8%] | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 99.9% [99.8%, 99.9%] | 100.0% [100.0%, 100.0%] | 99.9% [99.7%, 100.0%] |
| Valid-query rate | 26.0% [26.0%, 26.1%] | 99.3% [80.5%, 99.7%] | 96.3% [95.7%, 99.3%] | 99.4% [99.3%, 99.5%] | 95.5% [95.0%, 96.3%] | 98.3% [95.5%, 98.8%] | 95.3% [93.8%, 96.4%] |
| Statements/s | 298.4 [239.2, 380.5] | 67.2 [50.7, 80.8] | 39.9 [22.9, 50.3] | 45.0 [40.2, 53.6] | 32.5 [26.8, 39.6] | 42.8 [34.5, 63.2] | 31.0 [29.9, 44.1] |
| Test cases | 1,074,240 [861,265, 1,369,863] | 71,228 [55,628, 85,181] | 58,601 [33,282, 73,066] | 64,923 [56,888, 75,545] | 48,222 [35,826, 60,564] | 63,655 [49,712, 87,554] | 46,754 [44,300, 66,758] |
| Unique bug candidates | 0 [0, 0] | 1 [0, 4] | 1 [1, 17] | 1 [1, 4] | 1 [0, 3] | 3 [0, 10] | 1 [0, 3] |
| Known bugs reproduced | 0 [0, 0] | 0 [0, 0] | 0 [0, 0] | 0 [0, 0] | 0 [0, 0] | 0 [0, 0] | 0 [0, 0] |
| Time to first bug (s) | - | 1,514.6 [329.3, 3,056.9] | 1,956.4 [918.7, 3,138.0] | 470.9 [152.7, 3,277.4] | 280.0 [192.7, 1,872.8] | 598.6 [68.0, 799.1] | 953.9 [138.6, 2,079.8] |

## Pairwise comparisons

`A12` is the probability that B beats A on that metric (0.5 = no difference; lower-is-better metrics are flipped). `p` is from a two-sided Mann-Whitney U test.

| A | B | Metric | Median A | Median B | p | A12 | Effect |
|---|---|---|---:|---:|---:|---:|---|
| Random/Mutation | Grammar | Line coverage | 22.2% | 36.7% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar | Branch coverage | 15.1% | 27.1% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar | SQL features | 23 | 101 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar | SQL feature coverage | 15.5% | 68.2% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar | Feature pairs | 57 | 2,517 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar | Distinct query shapes | 8,407 | 80,477 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar | Distinct plan shapes | 43 | 20,279 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar | Plan-variant runs | 154,440 | 105,372 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar | Parse-valid rate | 33.6% | 100.0% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar | Valid-query rate | 26.0% | 99.3% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar | Statements/s | 298.4 | 67.2 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar | Test cases | 1,074,240 | 71,228 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar | Unique bug candidates | 0 | 1 | 0.025 | 0.90 | large |
| Random/Mutation | Grammar | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Line coverage | 36.7% | 36.2% | 0.421 | 0.32 | medium |
| Grammar | Grammar+Oracles | Branch coverage | 27.1% | 26.7% | 0.421 | 0.32 | medium |
| Grammar | Grammar+Oracles | SQL features | 101 | 101 | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | SQL feature coverage | 68.2% | 68.2% | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Feature pairs | 2,517 | 2,471 | 0.008 | 0.00 | large |
| Grammar | Grammar+Oracles | Distinct query shapes | 80,477 | 73,157 | 0.222 | 0.24 | large |
| Grammar | Grammar+Oracles | Distinct plan shapes | 20,279 | 34,313 | 0.095 | 0.84 | large |
| Grammar | Grammar+Oracles | Plan-variant runs | 105,372 | 166,718 | 0.095 | 0.84 | large |
| Grammar | Grammar+Oracles | Parse-valid rate | 100.0% | 100.0% | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Valid-query rate | 99.3% | 96.3% | 0.841 | 0.44 | small |
| Grammar | Grammar+Oracles | Statements/s | 67.2 | 39.9 | 0.008 | 0.00 | large |
| Grammar | Grammar+Oracles | Test cases | 71,228 | 58,601 | 0.222 | 0.24 | large |
| Grammar | Grammar+Oracles | Unique bug candidates | 1 | 1 | 0.656 | 0.60 | small |
| Grammar | Grammar+Oracles | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| Grammar | Grammar+Oracles | Time to first bug (s) | 1,514.6 | 1,956.4 | 0.730 | 0.40 | small |
| Grammar+Oracles | Grammar+Oracles, no bandit | Line coverage | 36.2% | 36.2% | 1.000 | 0.52 | negligible |
| Grammar+Oracles | Grammar+Oracles, no bandit | Branch coverage | 26.7% | 26.8% | 0.690 | 0.60 | small |
| Grammar+Oracles | Grammar+Oracles, no bandit | SQL features | 101 | 101 | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles, no bandit | SQL feature coverage | 68.2% | 68.2% | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles, no bandit | Feature pairs | 2,471 | 2,517 | 0.012 | 1.00 | large |
| Grammar+Oracles | Grammar+Oracles, no bandit | Distinct query shapes | 73,157 | 75,216 | 0.421 | 0.68 | medium |
| Grammar+Oracles | Grammar+Oracles, no bandit | Distinct plan shapes | 34,313 | 23,997 | 0.151 | 0.20 | large |
| Grammar+Oracles | Grammar+Oracles, no bandit | Metamorphic checks run | 41,740 | 31,491 | 0.151 | 0.20 | large |
| Grammar+Oracles | Grammar+Oracles, no bandit | Plan-variant runs | 166,718 | 125,192 | 0.151 | 0.20 | large |
| Grammar+Oracles | Grammar+Oracles, no bandit | Parse-valid rate | 100.0% | 100.0% | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles, no bandit | Valid-query rate | 96.3% | 99.4% | 0.016 | 0.96 | large |
| Grammar+Oracles | Grammar+Oracles, no bandit | Statements/s | 39.9 | 45.0 | 0.151 | 0.80 | large |
| Grammar+Oracles | Grammar+Oracles, no bandit | Test cases | 58,601 | 64,923 | 0.421 | 0.68 | medium |
| Grammar+Oracles | Grammar+Oracles, no bandit | Unique bug candidates | 1 | 1 | 0.906 | 0.46 | negligible |
| Grammar+Oracles | Grammar+Oracles, no bandit | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| Grammar+Oracles | Grammar+Oracles, no bandit | Time to first bug (s) | 1,956.4 | 470.9 | 0.548 | 0.64 | medium |
| Grammar+Oracles, no bandit | +LLM fragments | Line coverage | 36.2% | 35.7% | 0.032 | 0.08 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Branch coverage | 26.8% | 26.5% | 0.056 | 0.12 | large |
| Grammar+Oracles, no bandit | +LLM fragments | SQL features | 101 | 104 | 0.004 | 1.00 | large |
| Grammar+Oracles, no bandit | +LLM fragments | SQL feature coverage | 68.2% | 70.3% | 0.004 | 1.00 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Feature pairs | 2,517 | 2,461 | 0.012 | 0.00 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Distinct query shapes | 75,216 | 55,056 | 0.032 | 0.08 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Distinct plan shapes | 23,997 | 25,972 | 0.151 | 0.80 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Metamorphic checks run | 31,491 | 33,230 | 1.000 | 0.48 | negligible |
| Grammar+Oracles, no bandit | +LLM fragments | Plan-variant runs | 125,192 | 131,438 | 1.000 | 0.48 | negligible |
| Grammar+Oracles, no bandit | +LLM fragments | Parse-valid rate | 100.0% | 99.9% | 0.007 | 0.00 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Valid-query rate | 99.4% | 95.5% | 0.008 | 0.00 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Statements/s | 45.0 | 32.5 | 0.008 | 0.00 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Test cases | 64,923 | 48,222 | 0.016 | 0.04 | large |
| Grammar+Oracles, no bandit | +LLM fragments | Unique bug candidates | 1 | 1 | 0.515 | 0.36 | medium |
| Grammar+Oracles, no bandit | +LLM fragments | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| Grammar+Oracles, no bandit | +LLM fragments | Time to first bug (s) | 470.9 | 280.0 | 0.786 | 0.60 | small |
| +LLM fragments | +LLM seeds | Line coverage | 35.7% | 35.6% | 1.000 | 0.48 | negligible |
| +LLM fragments | +LLM seeds | Branch coverage | 26.5% | 26.4% | 0.548 | 0.36 | medium |
| +LLM fragments | +LLM seeds | SQL features | 104 | 106 | 0.004 | 1.00 | large |
| +LLM fragments | +LLM seeds | SQL feature coverage | 70.3% | 71.6% | 0.004 | 1.00 | large |
| +LLM fragments | +LLM seeds | Feature pairs | 2,461 | 2,484 | 0.141 | 0.80 | large |
| +LLM fragments | +LLM seeds | Distinct query shapes | 55,056 | 75,506 | 0.032 | 0.92 | large |
| +LLM fragments | +LLM seeds | Distinct plan shapes | 25,972 | 29,274 | 0.151 | 0.80 | large |
| +LLM fragments | +LLM seeds | Metamorphic checks run | 33,230 | 42,488 | 0.151 | 0.80 | large |
| +LLM fragments | +LLM seeds | Plan-variant runs | 131,438 | 171,456 | 0.095 | 0.84 | large |
| +LLM fragments | +LLM seeds | Parse-valid rate | 99.9% | 100.0% | 0.007 | 1.00 | large |
| +LLM fragments | +LLM seeds | Valid-query rate | 95.5% | 98.3% | 0.056 | 0.88 | large |
| +LLM fragments | +LLM seeds | Statements/s | 32.5 | 42.8 | 0.016 | 0.96 | large |
| +LLM fragments | +LLM seeds | Test cases | 48,222 | 63,655 | 0.032 | 0.92 | large |
| +LLM fragments | +LLM seeds | Unique bug candidates | 1 | 3 | 0.287 | 0.72 | large |
| +LLM fragments | +LLM seeds | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| +LLM fragments | +LLM seeds | Time to first bug (s) | 280.0 | 598.6 | 1.000 | 0.50 | negligible |
| +LLM seeds | Grammar+Oracles+LLM | Line coverage | 35.6% | 35.7% | 0.690 | 0.60 | small |
| +LLM seeds | Grammar+Oracles+LLM | Branch coverage | 26.4% | 26.4% | 0.690 | 0.60 | small |
| +LLM seeds | Grammar+Oracles+LLM | SQL features | 106 | 106 | 1.000 | 0.50 | negligible |
| +LLM seeds | Grammar+Oracles+LLM | SQL feature coverage | 71.6% | 71.6% | 1.000 | 0.50 | negligible |
| +LLM seeds | Grammar+Oracles+LLM | Feature pairs | 2,484 | 2,457 | 0.151 | 0.20 | large |
| +LLM seeds | Grammar+Oracles+LLM | Distinct query shapes | 75,506 | 53,454 | 0.151 | 0.20 | large |
| +LLM seeds | Grammar+Oracles+LLM | Distinct plan shapes | 29,274 | 26,375 | 0.421 | 0.32 | medium |
| +LLM seeds | Grammar+Oracles+LLM | Metamorphic checks run | 42,488 | 30,520 | 0.151 | 0.20 | large |
| +LLM seeds | Grammar+Oracles+LLM | Plan-variant runs | 171,456 | 124,416 | 0.151 | 0.20 | large |
| +LLM seeds | Grammar+Oracles+LLM | Parse-valid rate | 100.0% | 99.9% | 0.007 | 0.00 | large |
| +LLM seeds | Grammar+Oracles+LLM | Valid-query rate | 98.3% | 95.3% | 0.032 | 0.08 | large |
| +LLM seeds | Grammar+Oracles+LLM | Statements/s | 42.8 | 31.0 | 0.222 | 0.24 | large |
| +LLM seeds | Grammar+Oracles+LLM | Test cases | 63,655 | 46,754 | 0.151 | 0.20 | large |
| +LLM seeds | Grammar+Oracles+LLM | Unique bug candidates | 3 | 1 | 0.287 | 0.28 | large |
| +LLM seeds | Grammar+Oracles+LLM | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| +LLM seeds | Grammar+Oracles+LLM | Time to first bug (s) | 598.6 | 953.9 | 0.400 | 0.25 | large |
| Random/Mutation | Grammar+Oracles | Line coverage | 22.2% | 36.2% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Branch coverage | 15.1% | 26.7% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | SQL features | 23 | 101 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | SQL feature coverage | 15.5% | 68.2% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Feature pairs | 57 | 2,471 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Distinct query shapes | 8,407 | 73,157 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Distinct plan shapes | 43 | 34,313 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Plan-variant runs | 154,440 | 166,718 | 0.841 | 0.56 | small |
| Random/Mutation | Grammar+Oracles | Parse-valid rate | 33.6% | 100.0% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Valid-query rate | 26.0% | 96.3% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Statements/s | 298.4 | 39.9 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles | Test cases | 1,074,240 | 58,601 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles | Unique bug candidates | 0 | 1 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| Random/Mutation | Grammar+Oracles, no bandit | Line coverage | 22.2% | 36.2% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Branch coverage | 15.1% | 26.8% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | SQL features | 23 | 101 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | SQL feature coverage | 15.5% | 68.2% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Feature pairs | 57 | 2,517 | 0.011 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Distinct query shapes | 8,407 | 75,216 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Distinct plan shapes | 43 | 23,997 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Plan-variant runs | 154,440 | 125,192 | 0.151 | 0.20 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Parse-valid rate | 33.6% | 100.0% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Valid-query rate | 26.0% | 99.4% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Statements/s | 298.4 | 45.0 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Test cases | 1,074,240 | 64,923 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Unique bug candidates | 0 | 1 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles, no bandit | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| Random/Mutation | +LLM fragments | Line coverage | 22.2% | 35.7% | 0.008 | 1.00 | large |
| Random/Mutation | +LLM fragments | Branch coverage | 15.1% | 26.5% | 0.008 | 1.00 | large |
| Random/Mutation | +LLM fragments | SQL features | 23 | 104 | 0.007 | 1.00 | large |
| Random/Mutation | +LLM fragments | SQL feature coverage | 15.5% | 70.3% | 0.007 | 1.00 | large |
| Random/Mutation | +LLM fragments | Feature pairs | 57 | 2,461 | 0.012 | 1.00 | large |
| Random/Mutation | +LLM fragments | Distinct query shapes | 8,407 | 55,056 | 0.008 | 1.00 | large |
| Random/Mutation | +LLM fragments | Distinct plan shapes | 43 | 25,972 | 0.012 | 1.00 | large |
| Random/Mutation | +LLM fragments | Plan-variant runs | 154,440 | 131,438 | 0.310 | 0.28 | large |
| Random/Mutation | +LLM fragments | Parse-valid rate | 33.6% | 99.9% | 0.008 | 1.00 | large |
| Random/Mutation | +LLM fragments | Valid-query rate | 26.0% | 95.5% | 0.008 | 1.00 | large |
| Random/Mutation | +LLM fragments | Statements/s | 298.4 | 32.5 | 0.008 | 0.00 | large |
| Random/Mutation | +LLM fragments | Test cases | 1,074,240 | 48,222 | 0.008 | 0.00 | large |
| Random/Mutation | +LLM fragments | Unique bug candidates | 0 | 1 | 0.072 | 0.80 | large |
| Random/Mutation | +LLM fragments | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| Random/Mutation | +LLM seeds | Line coverage | 22.2% | 35.6% | 0.008 | 1.00 | large |
| Random/Mutation | +LLM seeds | Branch coverage | 15.1% | 26.4% | 0.008 | 1.00 | large |
| Random/Mutation | +LLM seeds | SQL features | 23 | 106 | 0.007 | 1.00 | large |
| Random/Mutation | +LLM seeds | SQL feature coverage | 15.5% | 71.6% | 0.007 | 1.00 | large |
| Random/Mutation | +LLM seeds | Feature pairs | 57 | 2,484 | 0.012 | 1.00 | large |
| Random/Mutation | +LLM seeds | Distinct query shapes | 8,407 | 75,506 | 0.008 | 1.00 | large |
| Random/Mutation | +LLM seeds | Distinct plan shapes | 43 | 29,274 | 0.012 | 1.00 | large |
| Random/Mutation | +LLM seeds | Plan-variant runs | 154,440 | 171,456 | 0.548 | 0.64 | medium |
| Random/Mutation | +LLM seeds | Parse-valid rate | 33.6% | 100.0% | 0.007 | 1.00 | large |
| Random/Mutation | +LLM seeds | Valid-query rate | 26.0% | 98.3% | 0.008 | 1.00 | large |
| Random/Mutation | +LLM seeds | Statements/s | 298.4 | 42.8 | 0.008 | 0.00 | large |
| Random/Mutation | +LLM seeds | Test cases | 1,074,240 | 63,655 | 0.008 | 0.00 | large |
| Random/Mutation | +LLM seeds | Unique bug candidates | 0 | 3 | 0.025 | 0.90 | large |
| Random/Mutation | +LLM seeds | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |
| Random/Mutation | Grammar+Oracles+LLM | Line coverage | 22.2% | 35.7% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Branch coverage | 15.1% | 26.4% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | SQL features | 23 | 106 | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | SQL feature coverage | 15.5% | 71.6% | 0.007 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Feature pairs | 57 | 2,457 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Distinct query shapes | 8,407 | 53,454 | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Distinct plan shapes | 43 | 26,375 | 0.012 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Plan-variant runs | 154,440 | 124,416 | 0.310 | 0.28 | large |
| Random/Mutation | Grammar+Oracles+LLM | Parse-valid rate | 33.6% | 99.9% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Valid-query rate | 26.0% | 95.3% | 0.008 | 1.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Statements/s | 298.4 | 31.0 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Test cases | 1,074,240 | 46,754 | 0.008 | 0.00 | large |
| Random/Mutation | Grammar+Oracles+LLM | Unique bug candidates | 0 | 1 | 0.072 | 0.80 | large |
| Random/Mutation | Grammar+Oracles+LLM | Known bugs reproduced | 0 | 0 | 1.000 | 0.50 | negligible |

## Unique bug candidates

| Signature | Outcome | Strength | SQLSTATE | Message | Found by (trials) | Known bug |
|---|---|---|---|---|---|---|
| `cde9712bc8db` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (2), Grammar+Oracles+LLM (2), Grammar+Oracles (3), Grammar+Oracles, no bandit (4), +LLM fragments (1), +LLM seeds (3) | - |
| `65cd1cb9b0bf` | performance | message | - | row estimate rises when the WHERE clause is added: 0.0 -> 1.0 | Grammar+Oracles, no bandit (1), +LLM fragments (1), +LLM seeds (2) | - |
| `381a793a6668` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (1), +LLM seeds (2) | - |
| `cc7181e74014` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | +LLM fragments (1), +LLM seeds (2) | - |
| `ec8b42ef87ac` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles+LLM (1), Grammar+Oracles, no bandit (1), +LLM seeds (1) | - |
| `f6f5012e736d` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (1), Grammar+Oracles+LLM (1), +LLM seeds (1) | - |
| `4b8b72f7a937` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles, no bandit (2) | - |
| `8c5a13443e88` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (1), +LLM seeds (1) | - |
| `cc89286f2104` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar (1), +LLM seeds (1) | - |
| `015482844f3d` | wrong_result | diff | - | metamorphic check rls failed: 8 rows vs 8 rows | +LLM seeds (1) | - |
| `0a63efb279c0` | wrong_result | diff | - | result differs under plan variant no_hashagg: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `0a9d2595b187` | wrong_result | diff | - | result differs under plan variant mergejoin_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `18f0529fb3a5` | wrong_result | diff | - | result differs under plan variant nestloop_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `1961e6f50009` | wrong_result | diff | - | result differs under plan variant mergejoin_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `255e08379e82` | wrong_result | diff | - | result differs under plan variant no_memoize_material: 30 rows by default, 30 rows with variant | Grammar+Oracles (1) | - |
| `294a0263ac67` | wrong_result | diff | - | result differs under plan variant no_hashagg: 40 rows by default, 40 rows with variant | Grammar+Oracles+LLM (1) | - |
| `2a82e01aba28` | wrong_result | diff | - | metamorphic check rls failed: 1 rows vs 1 rows | +LLM fragments (1) | - |
| `2c5e24d151f2` | wrong_result | diff | - | result differs under plan variant index_scans: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `2fddf94021a5` | wrong_result | diff | - | result differs under plan variant parallel: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `33a7ff0b4100` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | Grammar+Oracles (1) | - |
| `34bfff77ad1b` | wrong_result | diff | - | result differs under plan variant no_join_reorder: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `37148893be33` | wrong_result | diff | - | result differs under plan variant nestloop_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `39f6aff66a57` | wrong_result | diff | - | result differs under plan variant index_scans: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `3d7440d06a82` | wrong_result | diff | - | result differs under plan variant mergejoin_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `3dc78dd95f41` | internal_error | message | XX000 | SubPlan found with no parent plan | Grammar (1) | - |
| `485efe9af4d4` | wrong_result | diff | - | result differs under plan variant parallel: 3 rows by default, 3 rows with variant | Grammar+Oracles, no bandit (1) | - |
| `4878fcb5fe4b` | assertion | stack | - | consuming input failed: server closed the connection unexpectedly | +LLM seeds (1) | - |
| `509c35b5c8cb` | assertion | stack | - | server connection lost while running metamorphic check tlp_where | +LLM seeds (1) | - |
| `7f006d106be6` | wrong_result | diff | - | result differs under plan variant mergejoin_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `82444bc96f83` | wrong_result | diff | - | metamorphic check rls failed: 1 rows vs 1 rows | +LLM fragments (1) | - |
| `84e36fe21cff` | internal_error | message | XX000 | corrupt MVNDistinct entry | +LLM seeds (1) | - |
| `8a4e039bb76f` | assertion | stack | - | server connection lost while running metamorphic check tlp_where | +LLM fragments (1) | - |
| `9492d3bdd347` | internal_error | message | XX000 | unrecognized node type: 25710 | Grammar+Oracles+LLM (1) | - |
| `a1fa96efeba7` | wrong_result | diff | - | result differs under plan variant no_join_reorder: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `a2b1d87d6765` | wrong_result | diff | - | metamorphic check rls failed: 78 rows vs 78 rows | Grammar+Oracles (1) | - |
| `c51c4dacc7f1` | internal_error | message | XX000 | no relation entry for relid 1 | Grammar (1) | - |
| `c5a5ed497011` | wrong_result | diff | - | result differs under plan variant partitionwise: 30 rows by default, 30 rows with variant | +LLM seeds (1) | - |
| `d36c7e921d92` | wrong_result | diff | - | result differs under plan variant nestloop_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `e1f8b06fdb26` | wrong_result | diff | - | metamorphic check rls failed: 1 rows vs 1 rows | Grammar+Oracles (1) | - |
| `e4d122d7026f` | wrong_result | diff | - | result differs under plan variant no_join_reorder: 8 rows by default, 8 rows with variant | Grammar+Oracles (1) | - |
| `ed62d088103f` | wrong_result | diff | - | result differs under plan variant mergejoin_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |
| `ffdfcbe7d92d` | wrong_result | diff | - | result differs under plan variant nestloop_only: 1 rows by default, 1 rows with variant | Grammar+Oracles (1) | - |

Each signature has a replayable `testcase.sql` under `<config>/trial-NN/failures/<signature>/`. Validate on a fresh server before reporting.
