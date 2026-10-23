# Execution plan (RQ1–RQ4)

Everything here is built, unit-tested (pytest) and smoke-tested on real servers.
What remains is running the campaigns for their full budgets and collecting the
numbers. Run the phases in order; each one says how long it takes, what to look
at, and what to send back.

Every server is built from the same commit of master, `26bd08fb` (the RQ3
benchmark base, 16 Oct 2026), and commits are mined only up to it, so all four
RQs measure the same code.

Machine assumptions: Linux or WSL2 (Ubuntu 22.04/24.04), 4+ cores, 16 GB RAM,
~25 GB free disk. All commands run from the repository root unless they start
with `cd src`. Everything lives under `$PGFUZZ_ROOT` (default `~/pgfuzz`).

```bash
export PGFUZZ_ROOT=$HOME/pgfuzz        # put this in ~/.bashrc
```

If you run as root (cloud boxes), create the user `pg` once (`useradd -m pg`):
the scripts then start every server as `pg`, because `initdb` refuses root.

| Phase | What | Machine time | Your time |
|---|---|---|---|
| 0 | builds + reference server | ~60 min | 5 min |
| 1 | LLM arm: mine commits, extend grammar (RQ4 ledger), on the coverage servers | 1–2 h | 10 min |
| 2 | RQ3: re-injected bugs, verify + campaign + attribution | ~5.5 h | 15 min |
| 3 | RQ1/RQ2/RQ4: coverage campaign, 6 arms | ~8 h | 10 min |
| 4 | triage every candidate, precision table (RQ2) | 1 h | 30 min |
| 5 | reports, figures, tables into the paper | 10 min | 20 min |

Phases 2 and 3 are overnight runs; they resume if interrupted (re-run the same
command; finished trials are kept).

---

## Phase 0: builds and servers (once)

```bash
bash scripts/setup_env.sh                          # master (asserts) + REL_18, ~25 min
bash scripts/rq1_servers.sh build                  # gcov build of master at the benchmark base, ~15 min
bash scripts/build_reinjected.sh                   # base + 23 reverted fixes, ~10 min
bash scripts/rq3_servers.sh build-solo             # base + one postgres binary per bug, ~25 min
bash scripts/ref_server.sh init && bash scripts/ref_server.sh start      # REL_18 on 5435
cd src && pip install -r requirements.txt && python3 -m pytest -q        # expect: 122 passed
```

**Check:** `build_reinjected.sh` ends with `installed into .../install/reinjected
(... = 26bd08fb... + 23 reverts)`. If a revert does not apply, send me the
output (your clone may be too shallow: `git -C ~/pgfuzz/src/postgres-master fetch --deepen 2000`).

## Phase 1: LLM arm (RQ4 data, and the fragments the LLM arms use)

Needs `ANTHROPIC_API_KEY` in the environment, or use `--mode manual` (the tool
writes each prompt to `results/llm/prompts/<key>.md`; paste it into Claude,
save the JSON answer as `results/llm/responses/<key>.json`, re-run).

```bash
bash scripts/rq1_servers.sh init 4 && bash scripts/rq1_servers.sh start 4   # gcov master, ports 5450-5453
cd src
python3 -m pgfuzz llm mine ~/pgfuzz/src/postgres-master --since 2026-06-29 \
    --until 26bd08fb5c069fbdf55867adc398cfca0f55d5c8 --exclude bench/reinjected/commits.txt --limit 40
python3 -m pgfuzz llm extend configs/rq1.yaml ../results/llm/commits.json --limit 30 --rounds 3 \
    --coverage-build $(bash ../scripts/rq1_servers.sh srcdir 0) --pg-repo ~/pgfuzz/src/postgres-master \
    --pg-head 26bd08fb5c069fbdf55867adc398cfca0f55d5c8
python3 -m pgfuzz llm report
```

`--exclude` is essential: the model must never see the fixes of the bugs RQ3
re-injects. `llm extend` gates every proposal on the clean master server of
worker 0 (parse, reachability, validity, seeds, and a diff-coverage gain on the
commit's changed lines). Expected cost: ~$0.10 per round, $5–10 for 30 commits
(the 9k-token system prompt is cached). Accepted fragments and seeds land in
`results/llm/fragments` and `results/llm/seeds`, where the LLM arms of RQ1 and
RQ3 read them.

**Screenshot:** the `llm report` table (acceptance rate, repair rounds,
rejections by stage, tokens, cost). **Send me:** `results/llm/ledger.jsonl`.

## Phase 2: RQ3, re-injected bugs (~5.5 h)

```bash
bash scripts/rq3_servers.sh init 4 && bash scripts/rq3_servers.sh start 4     # 28 servers
cd src
python3 -m pgfuzz bench verify configs/rq3.yaml          # 2 min: PoC of every bug on fixed/solo/injected
python3 -m pgfuzz selftest configs/rq3.yaml              # expect 10/10
python3 -m pgfuzz run configs/rq3.yaml -j 4              # 4 arms x 5 trials x 1 h = 5 h
python3 -m pgfuzz bench attribute configs/rq3.yaml ../results/rq3
python3 -m pgfuzz report ../results/rq3
```

**Check after `verify`:** 20 of 23 bugs observable, `all injected` column equal
to `symptom` everywhere (this is the table in `bench/reinjected/verify.json`).

**Screenshot:** the `verify` table; `bench attribute` table; the RQ3 section of
`results/rq3/report/report.md`. **Send me:** the whole `results/rq3/report/`
folder and `results/rq3/attribution.json`.

## Phase 3: RQ1, RQ2, RQ4 (~8 h)

```bash
bash scripts/rq3_servers.sh stop 4                        # free the cores
bash scripts/rq1_servers.sh start 4                       # if not still running from Phase 1
bash scripts/rq1_servers.sh coverage 0                    # prints a JSON line with lines_total > 0
cd src
python3 -m pgfuzz selftest configs/rq1.yaml
python3 -m pgfuzz run configs/rq1.yaml -j 4               # 6 arms x 5 trials x 1 h / 4 workers
python3 -m pgfuzz report ../results/rq1
```

Each worker writes its own gcov counters (`$PGFUZZ_ROOT/gcov/wN`), so parallel
trials do not mix coverage.

**Screenshot:** the summary table and the coverage-over-time plot in
`results/rq1/report/`. **Send me:** the `results/rq1/report/` folder.

## Phase 4: triage and precision (RQ2)

```bash
cd src
python3 -m pgfuzz triage configs/rq1.yaml ../results/rq1
python3 -m pgfuzz triage configs/rq3.yaml ../results/rq3   # failures not attributed to injected bugs
python3 -m pgfuzz precision ../triage/verdicts.yaml
```

Triage reproduces, reduces and writes `report.md` + `reduced.sql` per
candidate under `results/triage/`. **Send me** that folder; I will write the
verdicts (real / false positive / duplicate) into `triage/verdicts.yaml` and
draft upstream reports for anything real. Anything that still crashes on
current master after reduction is a new bug: tell me immediately.

## Phase 5: paper numbers

`results/*/report/*.tex` are LaTeX tables that drop into the paper
(`table_summary.tex`, `table_comparison.tex`, `table_rq3.tex`); the PNG plots go
to `paper/figs/`. I fill the remaining placeholders in the paper from these.

---

## For the progress meeting (live demo, 5 minutes)

All on the RQ3 servers (Phase 2 step 1):

1. `python3 -m pgfuzz sample configs/rq3.yaml --name grammar_mm -n 3` shows
   generated test cases with metamorphic checks attached.
2. `python3 -m pgfuzz replay configs/rq3.yaml bench/reinjected/pocs/a8bb1a77.sql --expect-bug`
   shows a re-injected assertion failure being caught (rewriteManip.c).
3. `python3 -m pgfuzz bench verify configs/rq3.yaml` shows the benchmark table live.
4. `python3 -m pgfuzz triage ...` on a fresh candidate shows reduction from
   ~100 tokens to a one-line reproducer.
