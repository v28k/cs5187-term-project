# Handoff: Check the Tree (CS-5187 term project report): state on 2026-11-13

## 1. The project in one paragraph

Arbor (`pgfuzz` in the code) is a grammar-aware fuzzer for PostgreSQL that keeps every generated
query as a typed derivation tree, attaches metamorphic oracles as tree rewrites, compares each
query with plan variants and with the last release, and extends its grammar from recent commits
with an LLM behind a server-side validation gate. Main result: ten PostgreSQL bugs reported, eight
fixed upstream (six with our patches); the typed grammar covers 36.7% of backend lines against
22.2% for random mutation.

## 2. Venue

| Item | Value |
|---|---|
| Venue / track | CS-5187 term project report, FSE format |
| Format | ACM Primary Article Template, `acmart` `sigconf` (course deliverables page); named authors and a signed statement of contributions, so not anonymous |
| Page limit | 12 pages of text and figures (`paper.conf`) |
| Deadline | Fri 13 Nov 2026, 23:59 IST |
| Submission | PDF `paper/paper.pdf`, sources in `paper/`, repository with reproduction instructions |

## 3. Where things are

* Paper: this directory (`sections/`, `macros.tex`, `figures/`, `tables/`); `make`, `make check`.
* Tool: `src/` (see `src/README.md`); scripts in `scripts/`.
* Raw data behind the numbers: `runs/memberB-rq1-llm/` (RQ1, RQ2, RQ4), `runs/memberA-rq3/` (RQ3),
  `triage/verdicts.yaml` (RQ2 verdicts). `python3 paper/scripts/make_tables.py` regenerates
  `tables/rq1.tex` to `tables/rq4.tex` and the two plots from these files (checked 2026-11-13:
  output identical to the committed tables).

## 4. Numbers in the paper and their sources

Reference environment: Ubuntu 24.04.5 LTS (WSL2, 24 logical cores) for RQ1/RQ2/RQ4, a second laptop
for RQ3 (`runs/*/env.txt`); PostgreSQL master `26bd08fb` with assertions, reference 18.6;
Python 3.13.16, versions in `src/requirements-lock.txt`.

| Claim | Value | Source file |
|---|---|---|
| Lines covered, Random vs Grammar | 22.2% vs 36.7% (A12 = 1.00, p = 0.008) | `runs/memberB-rq1-llm/trials/` via `make_tables.py` -> `tables/rq1.tex` |
| Valid statements, Random vs Grammar | 26.0% vs 99.3% | `tables/rq1.tex` |
| SQL features, Random vs Grammar | 23 vs 101 (catalogue of 148) | `tables/rq1.tex` |
| Test cases, Random vs Grammar | 1,074,240 vs 71,228 (15 times) | `tables/rq1.tex` |
| Plan shapes, Grammar vs Grammar+Oracles | 20,279 vs 34,313 (A12 = 0.84, p = 0.095) | `tables/rq1.tex`, script output |
| Plan shapes and validity, flat arm | 23,997 (A12 = 0.80, p = 0.15); validity 99.4% vs 96.3% | `tables/rq1.tex`, script output |
| Lines, Grammar+Oracles vs +LLM | 36.2% vs 35.7% (p = 0.42) | `tables/rq1.tex`, script output |
| Features with LLM | 101 to 104 to 106 (A12 = 1.00, p = 0.004) | script output |
| Throughput with and without oracles | 40 vs 67 statements per second | `runs/memberB-rq1-llm/report/report.md` |
| Candidates triaged | 93: 28 flaky, 8 real, 15 duplicates, 42 false positives | `triage/verdicts.yaml` -> `tables/rq2.tex` |
| Precision | 8/50 = 0.16; 23/65 = 0.35 with duplicates | `tables/rq2.tex` |
| Benchmark | 23 reverted fixes; 20 observable (8 wrong results, 5 internal errors, 4 assertions, 2 missing errors, 1 wrong error) | `runs/memberA-rq3/verify.json`, `src/bench/` |
| RQ3 findings per arm | Random 0, Grammar 1, Grammar+Oracles 2, +LLM 2 of 20 | `runs/memberA-rq3/attribution.json` -> `tables/rq3.tex` |
| RQ3 wrong-result failures | 30: 11 on fixed server, 19 on none, 0 on a solo server | `runs/memberA-rq3/attribution.json` |
| LLM gate | 4 of 10 commits accepted; 25 rounds; mean validity 36.5%; 34 changed lines; 7 of 7 rewrites | `runs/memberB-rq1-llm/llm/` -> `tables/rq4.tex` |
| LLM tokens | 327,856 input, 170,931 output; cost 0 USD | `tables/rq4.tex` |
| Models used | 9 answers gemini-3.6-flash, 2 gemini-3.8-flash, 14 gemini-3-flash-preview | `runs/memberB-rq1-llm/llm/` (ledger) |
| Reported bugs and states | 10 reported, 8 fixed upstream, 6 with our patches | `README.md` (bug table with links) |
| Rediscovery | 10 of 10 known bugs in one 150-second run | `scripts/reproduce.sh` output; `docs/evidence/rediscovery/` |
| Grammar size | 78 rules, 421 alternatives, 13 types, 628 lines in the campaigns; 83 / 437 / 651 lines now | `src/grammar/postgres.pgg` (campaign version: commit `f1e8ec5`) |
| Code size and tests | about 11,000 lines of Python; 151 unit tests | `src/pgfuzz/`, `cd src && python -m pytest` |
| Reduction example | 79 tokens with tree + token reduction, 116 with token reduction alone | `docs/evidence/tree_reduction/README.md` |
| Generalized fuzzer: validity | DuckDB 96.3%, SQLite 97.7%, Turso 93.3%, DataFusion 79.4% | branch `generalized`, `docs/generalized/` |
| Generalized fuzzer: normalizers | disagreements 28.7% to 3.6% | branch `generalized`, `docs/generalized/` |
| Generalized fuzzer: rule kernels | rule pairs DuckDB 307 to 386, DataFusion 241 to 276, SQLite 86 to 182 | branch `generalized`, `docs/generalized/results/rq8_kernels_2026-11-12.md` |
| Generalized fuzzer: bugs | 14 found, 9 already fixed upstream, 5 filed with fixes | branch `generalized`, `docs/bughunt/FINDINGS_2026-11.md`, `docs/generalized/LEDGER.md` |

## 5. Open decisions

None. Format: `sigconf` with names, as the course deliverables page requires (see the comment block
at the top of `main.tex`).

## 6. Paper TODOs

None: `make check` reports zero `\todo` and zero `\num`.

## 7. Lessons / pitfalls

* Oracle precision, not generator reach, limited the fuzzer; every rewrite needs a soundness check.
* A rewrite proposed by the LLM passed the gate although it changes the collation; testing on
  samples is not proof.
