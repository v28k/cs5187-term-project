# Team runbook: running the experiments (24 Oct 2026 onwards)

The code is finished and tested (138 tests). **Nobody changes code.** This runbook
splits `docs/EXECUTION_PLAN.md` between two team members. Each one runs their part
on their own laptop, collects outputs and screenshots exactly as listed below, and
pushes them to the repository. Then we analyse everything, fill the paper and
finish the submission.

| | Member A (suggested: Bhuvan) | Member B (suggested: Gowtham) |
|---|---|---|
| Research questions | **RQ3** (re-injected bugs) + presentation evidence | **RQ4** (LLM arm), **RQ1/RQ2** (coverage campaign) |
| Phases of EXECUTION_PLAN.md | 0 (RQ3 builds), 2, 4 (RQ3 part) | 0 (RQ1 builds), 1, 3, 4 (RQ1 part) |
| Machine time | ~1.5 h builds + ~6 h overnight run | ~1 h builds + ~2 h LLM + ~9 h overnight run |
| Your own time | ~1.5 h spread over two days | ~1.5 h spread over two days |
| Branch | `runs-memberA` | `runs-memberB` |
| Output folder (in the repo) | `runs/memberA-rq3/` | `runs/memberB-rq1-llm/` |
| Depends on | Member B's LLM output (only for the last RQ3 arm) | nothing |

**Why split this way:** all arms of one experiment must run on the **same machine**,
because throughput and coverage depend on the hardware. So RQ3 runs entirely on A's
laptop and RQ1 entirely on B's laptop. Never split one experiment's arms across
laptops.

## Timeline

| When | Member A | Member B |
|---|---|---|
| Day 1 (24 Oct), morning | Part 0 setup, Part A1 builds | Part 0 setup, Part B1 builds |
| Day 1, afternoon | A2 benchmark check, A3 evidence screenshots | **B2 LLM arm, then push its output** (A needs it) |
| Day 1, evening → night | A4 RQ3 run (first 3 arms, then the LLM arm) | B3 RQ1 run (overnight, ~9 h) |
| Day 2 (25 Oct) | A5 attribution, report, triage; push | B4 report, triage, precision; push |
| Day 2 evening | We analyse, then write the paper numbers and the meeting 2 slides | |

Meeting 2 is 26–30 Oct, so everything must be pushed by **25 Oct night**.

---

## Part 0: setup (both members, ~20 min of your time)

### 0.1 Machine

* Linux (Ubuntu 22.04/24.04) or **Windows with WSL2 Ubuntu 24.04**. Not macOS.
* At least 4 cores, 16 GB RAM, **40 GB free disk** (Member A builds 25 PostgreSQL
  binaries). Check with `nproc`, `free -g`, `df -h ~`.
* With 8 GB RAM or 2 cores, use `-j 2` instead of `-j 4` everywhere (the run takes
  twice as long, results stay valid; write it in `env.txt`).

**Windows only (WSL2):**
1. PowerShell as administrator: `wsl --install -d Ubuntu-24.04`, reboot, create a user.
2. Create `C:\Users\<you>\.wslconfig` with
   ```
   [wsl2]
   memory=12GB
   processors=4
   ```
   then `wsl --shutdown` in PowerShell and reopen Ubuntu.
3. Work **inside the Linux home** (`~`), never under `/mnt/c` (10× slower).

**Keep the laptop awake for the overnight runs:** plug it in. On Windows: Settings →
System → Power → Screen and sleep → "Never" when plugged in. Also set closing the
lid to "Do nothing". On Ubuntu: Settings → Power → Automatic suspend → Off.

### 0.2 Get the repository

The repository owner adds you as a collaborator on GitHub (repo Settings →
Collaborators → Add people). Accept the invitation email, then:

```bash
sudo apt-get update && sudo apt-get install -y git tmux python3-pip python3-venv
git config --global user.name  "<your name>"
git config --global user.email "<your GitHub email>"
cd ~ && git clone https://github.com/v28k/cs5187-term-project.git
cd cs5187-term-project
git checkout -b runs-memberA        # Member B: runs-memberB
echo 'export PGFUZZ_ROOT=$HOME/pgfuzz' >> ~/.bashrc && source ~/.bashrc
```

Authenticate pushes with a GitHub personal access token (GitHub → Settings →
Developer settings → Tokens) or `gh auth login`.

### 0.3 Always run long commands inside tmux

```bash
tmux new -s pg          # start a session; detach with Ctrl-b then d
tmux attach -t pg       # come back later
```
If a long run stops (laptop slept, terminal closed), **re-run the same command**:
finished trials are kept and the run resumes.

### 0.4 Record everything

Make your output folder and an environment record (replace memberA / memberA-rq3
with memberB / memberB-rq1-llm for B):

```bash
cd ~/cs5187-term-project
OUT=~/cs5187-term-project/runs/memberA-rq3      # Member B: runs/memberB-rq1-llm
mkdir -p $OUT/logs $OUT/screenshots
echo "export OUT=$OUT" >> ~/.bashrc
{ date; uname -a; nproc; free -g; df -h ~; python3 --version; git rev-parse HEAD; } > $OUT/env.txt
```

**Rule for every command below:** append `2>&1 | tee $OUT/logs/<name>.txt`, as
written. That file is the evidence. Screenshots go to `$OUT/screenshots/` with the
exact file names given (PNG; Windows: Win+Shift+S, then paste into Paint and save;
Ubuntu: PrtSc). Take each screenshot of the terminal showing the command **and**
its output.

### 0.5 Common build (both members, ~25 min machine time)

```bash
cd ~/cs5187-term-project
bash scripts/setup_env.sh 2>&1 | tee $OUT/logs/00_setup_env.txt          # master + REL_18, ~25 min
cd src && python3 -m pip install --user -r requirements.txt 2>&1 | tail -3
python3 -m pytest -q 2>&1 | tee $OUT/logs/01_pytest.txt                   # expect: 138 passed
cd ..
```
**Check:** the last line of `01_pytest.txt` is `138 passed`. If not, stop and send us
the file. Screenshot: `00_pytest.png`.

(If `pip install --user` complains about an "externally managed environment", use
`python3 -m pip install --user --break-system-packages -r requirements.txt`.)

---

## Member A: RQ3, the re-injected bug benchmark, and presentation evidence

### A1. Builds (~1 h machine time)

```bash
cd ~/cs5187-term-project
bash scripts/build_reinjected.sh 2>&1 | tee $OUT/logs/A1_build_reinjected.txt   # ~10 min
bash scripts/rq3_servers.sh build-solo 2>&1 | tee $OUT/logs/A1_build_solo.txt   # ~25 min
bash scripts/ref_server.sh init && bash scripts/ref_server.sh start 2>&1 | tee $OUT/logs/A1_ref_server.txt
bash scripts/rq3_servers.sh init 4 && bash scripts/rq3_servers.sh start 4 2>&1 | tee $OUT/logs/A1_rq3_servers.txt
```
**Check:** `A1_build_reinjected.txt` ends with `installed into .../install/reinjected
(... = 26bd08fb... + 23 reverts)`. If a revert fails, run
`git -C ~/pgfuzz/src/postgres-master fetch --deepen 2000` and repeat; if it still
fails, send us the file.

### A2. Benchmark check (5 min)

```bash
cd ~/cs5187-term-project/src
python3 -m pgfuzz bench verify configs/rq3.yaml 2>&1 | tee $OUT/logs/A2_bench_verify.txt
python3 -m pgfuzz selftest configs/rq3.yaml 2>&1 | tee $OUT/logs/A2_selftest.txt
```
**Check:** 20 of 23 bugs observable, and the `all injected` column equals the
`symptom` column everywhere; selftest says `10/10 checks passed`.
Screenshots: `A2_bench_verify.png` (the whole table), `A2_selftest.png`.

### A3. Presentation evidence (fills the PLACEHOLDER boxes in our slides, 20 min)

Use the servers from A1: the reference 18.6 server is on port 5435, and the
re-injected master is on 5440. Run each block and take the named screenshot.

```bash
cd ~/cs5187-term-project/src
# a) BUG-02 live on 18.6 and on master (slide 4)
for p in 5435 5440; do psql -h 127.0.0.1 -p $p -U postgres -c "SELECT version()" -c "
SELECT c, '(,)'::int4range @> c AS a, 'empty'::int4range @> c AS b, NOT ('empty'::int4range @> c) AS d
FROM (VALUES (NULL::int), (1)) v(c);" -c "EXPLAIN VERBOSE SELECT '(,)'::int4range @> c FROM (VALUES (NULL::int), (1)) v(c);"; done 2>&1 | tee $OUT/logs/A3_bug02.txt
```
Screenshot `A3_bug02.png`. The NULL row must show `t | f | t` on both servers (that is
the bug), and EXPLAIN must show `Output: true`.

```bash
# b) a generated test case with its metamorphic checks (demo step 1)
python3 -m pgfuzz sample configs/rq3.yaml --name grammar_mm -n 3 2>&1 | tee $OUT/logs/A3_sample.txt
# c) validity of the generator (demo step 2)
python3 -m pgfuzz sample configs/rq3.yaml --name grammar_mm -n 300 --execute 2>&1 | tee $OUT/logs/A3_validity.txt
# d) a re-injected assertion being caught (demo step 3)
python3 -m pgfuzz replay configs/rq3.yaml bench/reinjected/pocs/a8bb1a77.sql --expect-bug 2>&1 | tee $OUT/logs/A3_replay.txt
# e) triage with tree reduction on a real BUG-01 test case (slide 12)
python3 -m pgfuzz triage configs/rq3.yaml ../docs/evidence/tree_reduction/original.sql --out ../results/triage_demo 2>&1 | tee $OUT/logs/A3_triage.txt
cp -r ../results/triage_demo $OUT/triage_demo
```
Screenshots: `A3_sample.png`, `A3_validity.png` (the summary at the end),
`A3_replay.png`, `A3_triage.png` (the "reduced to ..." line), and
`A3_upstream_report.png` (open `$OUT/triage_demo/*/upstream_report.txt` in an editor).

**Commit and push now** (see "How to push" at the end), so we can start the slides.

### A4. RQ3 campaign (overnight; inside tmux)

The last arm (`grammar_llm`) needs Member B's LLM output. Start with the other
three arms right away:

```bash
tmux new -s rq3
cd ~/cs5187-term-project/src
python3 -m pgfuzz run configs/rq3.yaml -j 4 --only random,grammar,grammar_mm 2>&1 | tee $OUT/logs/A4_run_part1.txt   # ~4 h
```
When Member B has pushed `runs/memberB-rq1-llm/llm/` (B2) **and** part 1 is done:

```bash
cd ~/cs5187-term-project && git fetch origin && git checkout origin/runs-memberB -- runs/memberB-rq1-llm/llm
mkdir -p results && rm -rf results/llm && cp -r runs/memberB-rq1-llm/llm results/llm
git reset -q runs/memberB-rq1-llm && rm -rf runs/memberB-rq1-llm   # keep B's folder out of your branch
ls results/llm/fragments | head          # must list .pgg files
cd src && python3 -m pgfuzz run configs/rq3.yaml -j 4 --only grammar_llm 2>&1 | tee $OUT/logs/A4_run_part2.txt   # ~1.5 h
```
(If B's output is not there by the time part 1 ends, wait; do not run the LLM arm
without it.)

### A5. Attribution, report, triage (Day 2, ~1 h machine time)

```bash
cd ~/cs5187-term-project/src
python3 -m pgfuzz bench attribute configs/rq3.yaml ../results/rq3 2>&1 | tee $OUT/logs/A5_attribute.txt
python3 -m pgfuzz report ../results/rq3 2>&1 | tee $OUT/logs/A5_report.txt
python3 -m pgfuzz triage configs/rq3.yaml ../results/rq3 --out ../results/triage_rq3 2>&1 | tee $OUT/logs/A5_triage.txt
```
Screenshots: `A5_attribute.png` (the table), `A5_report_rq3.png` (open
`results/rq3/report/report.md` and capture the RQ3 table and the time-to-bug lines).

Copy the outputs into your folder:
```bash
cd ~/cs5187-term-project
cp -r results/rq3/report $OUT/report
cp results/rq3/attribution.json $OUT/ 2>/dev/null; cp src/bench/reinjected/verify.json $OUT/verify.json
mkdir -p $OUT/trials $OUT/failures
(cd results/rq3 && find . \( -name summary.json -o -name manifest.json \) -exec cp --parents {} $OUT/trials/ \;)
(cd results/rq3 && find . -path '*/failures/*' \( -name failure.json -o -name testcase.sql \) -exec cp --parents {} $OUT/failures/ \;)
cp -r results/triage_rq3 $OUT/triage_rq3
tar czf ~/rq3_full_results.tar.gz -C ~/cs5187-term-project results/rq3
du -sh $OUT ~/rq3_full_results.tar.gz
```
Upload `~/rq3_full_results.tar.gz` to the shared Google Drive folder and put the link
in `$OUT/LINKS.md`. Push (below). Then stop the servers:
`bash scripts/rq3_servers.sh stop 4 && bash scripts/ref_server.sh stop`.

---

## Member B: LLM arm (RQ4) and the coverage campaign (RQ1, RQ2)

### B1. Builds (~20 min machine time)

```bash
cd ~/cs5187-term-project
bash scripts/rq1_servers.sh build 2>&1 | tee $OUT/logs/B1_build_cov.txt         # gcov build at 26bd08fb, ~15 min
bash scripts/rq1_servers.sh init 4 && bash scripts/rq1_servers.sh start 4 2>&1 | tee $OUT/logs/B1_servers.txt
bash scripts/rq1_servers.sh coverage 0 2>&1 | tee $OUT/logs/B1_coverage_check.txt   # JSON with lines_total > 0
cd src && python3 -m pgfuzz selftest configs/rq1.yaml 2>&1 | tee $OUT/logs/B1_selftest.txt   # 10/10
```
Screenshots: `B1_coverage_check.png`, `B1_selftest.png`.

### B2. LLM arm (1–2 h machine time; do this first on Day 1, A waits for it)

You need an Anthropic API key (expected cost about $5–10). Set it **only in the
shell**, never in a file in the repository:
```bash
export ANTHROPIC_API_KEY=sk-ant-...        # do not commit, do not paste into any file
cd ~/cs5187-term-project/src
python3 -m pip install --user anthropic
python3 -m pgfuzz llm mine ~/pgfuzz/src/postgres-master --since 2026-06-29 \
    --until 26bd08fb5c069fbdf55867adc398cfca0f55d5c8 --exclude bench/reinjected/commits.txt --limit 40 \
    2>&1 | tee $OUT/logs/B2_mine.txt
python3 -m pgfuzz llm extend configs/rq1.yaml ../results/llm/commits.json --limit 30 --rounds 3 \
    --coverage-build $(bash ../scripts/rq1_servers.sh srcdir 0) --pg-repo ~/pgfuzz/src/postgres-master \
    --pg-head 26bd08fb5c069fbdf55867adc398cfca0f55d5c8 2>&1 | tee $OUT/logs/B2_extend.txt
python3 -m pgfuzz llm report 2>&1 | tee $OUT/logs/B2_llm_report.txt
```
**No API key?** Add `--mode manual --limit 10` to `llm extend`. It stops at each
prompt and tells you the file `results/llm/prompts/<key>.md`; paste that into
Claude (claude.ai), save Claude's JSON answer as `results/llm/responses/<key>.json`,
and run the same command again until it finishes.

`--exclude` is essential: the model must never see the fixes of the RQ3 bugs.

Screenshots: `B2_extend_tail.png` (the end of extend), `B2_llm_report.png` (the
table: accepted/rejected, repair rounds, rejections by stage, tokens, cost).

**Push the LLM output immediately** (Member A needs it):
```bash
cd ~/cs5187-term-project
cp -r results/llm $OUT/llm
grep -rl "sk-ant-" $OUT/llm && echo "STOP: a key is in the output, tell us" || echo "no key in output"
```
then push (below) and tell Member A in the group chat.

### B3. RQ1 campaign (overnight, ~9 h; inside tmux)

```bash
tmux new -s rq1
cd ~/cs5187-term-project/src
python3 -m pgfuzz run configs/rq1.yaml -j 4 2>&1 | tee $OUT/logs/B3_run.txt
```
It runs 7 arms × 5 trials × 1 h with 4 in parallel. It resumes if interrupted
(same command).

### B4. Report, triage, precision (Day 2)

```bash
cd ~/cs5187-term-project/src
python3 -m pgfuzz report ../results/rq1 2>&1 | tee $OUT/logs/B4_report.txt
python3 -m pgfuzz triage configs/rq1.yaml ../results/rq1 --out ../results/triage_rq1 2>&1 | tee $OUT/logs/B4_triage.txt
python3 -m pgfuzz precision ../triage/verdicts.yaml 2>&1 | tee $OUT/logs/B4_precision_before.txt
```
Screenshots: `B4_summary_table.png` (the summary table in
`results/rq1/report/report.md`), `B4_coverage_plot.png` (the coverage-over-time PNG
in `results/rq1/report/`), `B4_plan_shapes_plot.png` (if present), `B4_triage.png`.

Copy and push:
```bash
cd ~/cs5187-term-project
cp -r results/rq1/report $OUT/report
mkdir -p $OUT/trials $OUT/failures
(cd results/rq1 && find . \( -name summary.json -o -name manifest.json \) -exec cp --parents {} $OUT/trials/ \;)
(cd results/rq1 && find . -path '*/failures/*' \( -name failure.json -o -name testcase.sql \) -exec cp --parents {} $OUT/failures/ \;)
cp -r results/triage_rq1 $OUT/triage_rq1
cp -r results/llm $OUT/llm        # refresh (the ledger may have grown)
tar czf ~/rq1_full_results.tar.gz -C ~/cs5187-term-project results/rq1 results/llm
du -sh $OUT ~/rq1_full_results.tar.gz
```
Upload `~/rq1_full_results.tar.gz` to the shared Google Drive folder, link it in
`$OUT/LINKS.md`, push, then `bash scripts/rq1_servers.sh stop 4`.

---

## How to push (both members, after each part)

```bash
cd ~/cs5187-term-project
git status --short                       # only files under runs/<your folder> may appear
git add runs/
git commit -m "Member A: <part done>"    # e.g. "Member A: A2 benchmark check, A3 evidence"
git push -u origin runs-memberA          # Member B: runs-memberB
```
Rules:
* Push **only** your `runs/<your folder>/`. Never commit `results/` (it is ignored on
  purpose), never edit files under `src/`, `paper/`, `docs/` or `triage/verdicts.yaml`.
* No file over 50 MB in git: big archives go to Google Drive (link in `LINKS.md`).
* Never commit an API key. If you did by mistake, tell us immediately (the key must
  be revoked; deleting the file is not enough).
* `git status` shows a modified file under `src/`? Run `git checkout -- <file>`
  (do not commit it) and tell us what command changed it.

## What your folder must contain at the end

**Member A, `runs/memberA-rq3/`:**
```
env.txt  LINKS.md  verify.json  attribution.json
logs/      00_setup_env, 01_pytest, A1_*, A2_bench_verify, A2_selftest, A3_*, A4_run_part1, A4_run_part2, A5_*
screenshots/  00_pytest, A2_bench_verify, A2_selftest, A3_bug02, A3_sample, A3_validity, A3_replay, A3_triage,
              A3_upstream_report, A5_attribute, A5_report_rq3   (.png)
report/    (results/rq3/report: report.md, table_*.tex, plots, csv)
trials/    (summary.json + manifest.json of every trial)
failures/  (failure.json + testcase.sql of every candidate)
triage_demo/  triage_rq3/
```

**Member B, `runs/memberB-rq1-llm/`:**
```
env.txt  LINKS.md
logs/      00_setup_env, 01_pytest, B1_*, B2_mine, B2_extend, B2_llm_report, B3_run, B4_*
screenshots/  00_pytest, B1_coverage_check, B1_selftest, B2_extend_tail, B2_llm_report,
              B4_summary_table, B4_coverage_plot, B4_plan_shapes_plot, B4_triage   (.png)
llm/       (results/llm: commits.json, ledger.jsonl, prompts/, responses/, fragments/, seeds/, rewrites/)
report/    (results/rq1/report)
trials/  failures/  triage_rq1/
```

## When something goes wrong

| Symptom | What to do |
|---|---|
| `initdb: cannot be run as root` | You are root: `sudo useradd -m pg` once; the scripts then start servers as `pg`. |
| `could not connect to server ... port 54xx` | Start the servers again (A1 / B1 start commands), then re-run the step. |
| `No space left on device` | `df -h ~`; delete `~/pgfuzz/src/*-wt` build trees only after the builds are installed; tell us. |
| A run stopped in the middle | Re-run the same `pgfuzz run` command; it resumes. |
| A build or revert fails | Send us the log file from `$OUT/logs/`; do not change anything. |
| Selftest is not 10/10, or pytest is not 138 passed | Stop, push your `logs/` folder and tell us. |
| Laptop much slower than 4 cores / 16 GB | Use `-j 2`, note it in `env.txt`. |

## What we do with your outputs

1. Check every log and screenshot against the expected values above.
2. Write the triage verdicts into `triage/verdicts.yaml` and compute precision (RQ2).
3. Put the tables (`table_*.tex`) and plots into the paper, replacing the blue
   placeholder numbers; write RQ1–RQ4 results and the discussion.
4. Fill the PLACEHOLDER boxes of the meeting-2 slides with your screenshots.
5. Prepare the submission: final paper PDF, repository README, artifact
   instructions, and the evidence folder.
