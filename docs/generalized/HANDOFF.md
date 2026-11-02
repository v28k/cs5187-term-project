# HANDOFF: everything a new person (or a new Claude session) needs to continue

Written 2 Nov 2026 at the end of a long working session. Read this file completely before
doing anything. Then read `docs/generalized/PLAN.md`, `docs/RESULTS_ANALYSIS.md` and
`docs/bughunt/new/E-01-*.md`, `E-02-*.md`.

---

## 0. Who, what, where

- **Project:** CS-5187 term project A3, "LLM-guided grammar-aware fuzzing of PostgreSQL".
  The tool is `pgfuzz` in code; in the anonymised paper it is called **Arbor** (`\tool`).
- **Team:** Venu Kummari (the owner of this work; files the PostgreSQL bugs, email
  venu2805k@gmail.com), Bhuvan Chilukuti (c.bhuvan@iitg.ac.in, "Member A"),
  Gowtham Reddy ("Member B", gowthamdoma18@gmail.com).
- **Repository (working):** https://github.com/v28k/cs5187-term-project
  - branch `main`: the finished course project (fuzzer, results, paper, slides).
  - branch `generalized`: the new work (generalize the fuzzer to other engines). **Work here.**
- **Repository the professor sees:** https://github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi
  (not yet updated; see section 6, item P4).
- **Course dates:** final presentation 12 Nov 2026; paper + repository due 13 Nov 2026.
- **Owner's GitHub email: v.kummari@iitg.ac.in** (use it as the author of every patch prepared for his pull requests).
- **New goal (from the professor):** turn the project into a high-level, target-independent
  fuzzer, find more bugs on other engines (GitHub issues/PRs, to build Venu's GitHub
  contribution record), and write a paper for an A* venue with a deadline around
  **January 2027** (ISSTA usually has a late-January deadline; check the CFPs).

## 1. Rules the owner gave (follow them exactly)

### 1a. Who does what
- **The fuzzer, the research and the repository are your work** (the person continuing this project).
  **Everything about bugs that is visible to the outside world belongs to the owner (Venu):** filing bug
  reports, GitHub issues, pull requests, comments or replies on issues/PRs/mailing lists/forums, emails to
  maintainers, security reports, and any public post about a bug. You must NOT do any of these, not even
  a comment or a "+1". Your bug work stays inside your repository (finding, validating, root-causing,
  fixing, writing the filing package) and in your messages to the owner.
- You prepare everything so the owner can file in minutes (section 1d), push it, and tell him.
- **PostgreSQL bug hunting is finished.** Do not hunt PostgreSQL any more; PostgreSQL stays as one
  target in the evaluation only (its results already exist).
- The owner and his team review your repository **periodically** and tell you what to change.
  Keep it reviewable: small commits, clear messages, a progress log (section 1c).

### 1b. Repository and commits
1. Create a **new public repository on your own GitHub account** (it is your work) named `generalized-sql-fuzzer`
   (or similar), containing the full history of branch `generalized` of
   https://github.com/v28k/cs5187-term-project:
   `git clone -b generalized https://github.com/v28k/cs5187-term-project && cd cs5187-term-project &&
   git remote rename origin upstream && gh repo create <you>/generalized-sql-fuzzer --public --source . --push`
   (or create it on the web and `git remote add origin ... && git push -u origin generalized`).
   Make `generalized` its default branch. Send the owner the URL.
2. Commit with **your own** git identity (any name/email you normally use). The only place where the
   owner's identity is required is the author of patches meant for his pull requests (section 1d):
   `Venu Kummari <v.kummari@iitg.ac.in>` (his GitHub email).
3. **Never mention Claude, Anthropic or "AI" in commit messages or in files** (no Co-Authored-By trailers,
   no "generated with" lines). Normal technical commit messages only.
4. **Commit and push as soon as a task or a meaningful part of it is done** (at least every hour of work):
   code + tests + docs together; never leave finished work uncommitted. Never force-push.
5. Never commit API keys, tokens or passwords; never commit large binaries (>20 MB) or build directories.
6. Keep `cd src && python -m pytest -q` green on every commit; add tests for every new component.

### 1c. Progress log (for the periodic reviews)
Keep `docs/generalized/PROGRESS.md` up to date: one dated entry per work session with what was done,
numbers measured (validity, throughput, candidates, bugs), what is next, and open questions for the owner.
Keep the task table in `docs/generalized/PLAN.md` current (status column).

### 1d. When you find a bug (any target)
1. Validate strictly: reproduce ≥3 times on the **newest** development version (DuckDB nightly
   `pip install --pre -U duckdb`, DataFusion `main`, …), minimal self-contained reproducer, check that the
   expected result is right (docs, standard, an equivalent query, another engine), find the versions affected,
   search for duplicates (the project's GitHub issues incl. closed ones, recent commits on `main`/nightly,
   release notes), find the root cause in the source when you can, and write a fix + a test in the project's
   own test format when the fix is clear (DuckDB: `test/sql/**/*.test` sqllogictest; DataFusion: `*.slt`).
   Doubtful findings go to `docs/bughunt/<target>/candidates.md`, not to a report.
2. Push a **filing package** to `docs/bughunt/<target>/<ID>-<slug>/`:
   - `report.md`: status, summary, severity, minimal reproducer, actual vs expected and why, versions,
     root cause, how our fuzzer found it (oracle, config, signature), duplicate search done (links/queries);
   - `issue.md`: the **exact text** for the GitHub issue (title + body in the project's issue template);
   - `repro.sql` (and a script if needed);
   - if a fix exists: `fix.patch` (made with `git format-patch` against the project's main, author
     `Venu Kummari <v.kummari@iitg.ac.in>`), the test file, and `pr.md` with the exact PR title and body;
   - `steps.md`: what the owner must do, in order (fork, apply patch, branch name, commands to run the tests).
3. List the package in PROGRESS.md under "Bug packages ready" (path, one line, confidence) and continue
   working; the owner checks the repository and files it. **Do not file it yourself.**

### 1e. How to work
- Make improvements and improvisations wherever they help the fuzzer or the paper; you do not need
  permission for engineering decisions. Record important design decisions in PROGRESS.md.
- Work fast but do not degrade quality. Measure before and after every change (validity, throughput,
  bugs/candidates, precision).
- Long jobs run in the background; wait on files/conditions; when asked to stop, stop background jobs
  **and** orphaned workers (section 7).
- **Never stop to ask the owner anything.** Decisions that are not engineering ones (target venue,
  paper authorship, AI-use statement, anonymous mirror URL, which bugs get filed and when) are left
  **blank / as clearly marked placeholders** (e.g. `VENUE: TBD`, `\todo{owner}`) and listed under
  "Open decisions" in `docs/generalized/PROGRESS.md`; the owner reviews the repository and fills them in.
  Keep working on everything else meanwhile.
- If an action is blocked (e.g. a permission for `cargo build`, a network host), note it under
  "Blocked" in PROGRESS.md, use a workaround if there is a sound one, and continue with other tasks.

## 2. Bugs: status on 2 Nov 2026 (keep this table current)

| # | Bug | Upstream | Status | Found by |
|---|---|---|---|---|
| 1 | JSON_TABLE does not assign collations (wrong result 17/18, assertion master) | BUG #19768 https://www.postgresql.org/message-id/19768-3633daa830be95db@postgresql.org | reported, patch sent, no reply | grammar fuzzer |
| 2 | range `@>` NULL element folded to true/false (wrong result 17, 18, master) | BUG #19793 https://www.postgresql.org/message-id/19793-16d3a1bf33dff0fb@postgresql.org | reported, patch sent | `(SELECT e)` rewrite oracle |
| 3 | MERGE into partitioned table: "SubPlan found with no parent plan" | BUG #19802 | confirmed by committer (Tender Wang), patch posted | grammar campaign |
| 4 | Parallel Append assertion | BUG #19803 | **fixed on master abda2a2c** (David Rowley) | LLM-fragment arm + TLP |
| 5 | to_char(NaN) breaks NORMALIZE (assertion) | BUG #19771 | **fixed in 776df8a6, authored by Gowtham** | grammar campaign |
| 6 | AUDIT-F1: NOT IN anti-join ignores implicit cast (wrong result 19/master) | https://www.postgresql.org/message-id/PN0P287MB090375874C6D5433282EC9DFA7642@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM | reported, patch | audit + TLP |
| 7 | AUDIT-F2: IGNORE NULLS frame scan never returns (ignores timeout and cancel) | https://www.postgresql.org/message-id/PN0P287MB09038F3BD9921EBACF5646F6A7632@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM | developer (Ishii) replied | audit; hang oracle |
| 8 | C-01: dependencies.c assertion, duplicate statistics expression | https://postgr.es/m/PN0P287MB0903563C70D8E5B81912E855A7602@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM | **fixed in b0392c26 (author Bhuvan, reviewed David Rowley, backpatched to 14)** | differential fuzzers |
| 9 | pg_restore_extended_stats accepts non-finite MCV freqs | pgsql-hackers patch | patch submitted | CERT oracle |
| 10 | **E-01**: corr()/regr_r2()/regr_slope() of constant input NULL serially, 1 with partial aggregation (regression from 64982876, master and REL_19) | **BUG #19826** (filed 2 Nov by Venu, patch sent) | waiting | plan-variant oracle |
| 11 | **E-02**: "plan should not reference subplan's variable" with Memoize + correlated ALL/ANY sublink (regression from f8da64e6, 2 Nov) | filed 2 Nov by Venu, Cc Richard Guo; **bug number not yet recorded** | waiting | internal-error oracle on master 633dee1b |

Also: duplicates found by our oracles but reported first by others: #19800, #19772, #19784.
Known upstream infra bug that hits our servers: #17731 (crash recovery "could not create file … File exists").

Counts used everywhere: 9 original reported, 4 answered, 2 confirmed, **3 fixed (2 by our team)**;
plus E-01 and E-02 filed on 2 Nov (11 reports in total).

**To do for bugs (PostgreSQL ones are the owner's; only record what he tells you):** E-02's bug number is unknown (leave it as a placeholder) and record it (E-02 md, RESULTS_ANALYSIS,
slides, paper); watch the threads of #19826 and E-02 and help answer reviewer questions;
the Teams post (owner has the text) still needs links for #19803, #19771, #19802, C-01, MCV thread.

## 3. What exists on `main` (finished work)

- `src/pgfuzz/`: the fuzzer (≈10.5k lines Python, 151 unit tests: `cd src && python -m pytest -q`).
  - `grammar/`: typed grammar DSL (`dsl.py`), engine with builtins (`engine.py`), generator
    (`generator.py`, seeds with declared checks via `parse_seed`), metamorphic rewrites on
    derivation trees (`rewrite.py`: TLP where/having/agg, NoREC, expr rewrites, pred rewrites incl.
    `pred:and_dup`, NOT NULL conjunct, ORDER BY drop, CTE materialise, table fence, RLS (skipped
    unless every protected table is inlined), CERT).
  - `reference/pg_executor.py`: PostgreSQL executor (savepoints, plan variants, metamorphic checks,
    CERT, plan shapes, **hang oracle** `hang_command` + `hang_grace_s`).
  - `eval/`: oracle classification (`oracle.py`, outcomes incl. HANG), digests (`differential.py`),
    signatures, known-bug catalog, stats.
  - `triage/`: reproduce, tree + token reduction, localization, upstream report drafts; `pgfuzz precision`.
  - `llm/`: commit miner, prompts, validation gate, ledger (the evaluation used Gemini Flash via manual mode).
  - `bench/`: RQ3 re-injected bug benchmark (23 reverted fixes).
- `src/grammar/postgres.pgg` (78 rules, ~437 alternatives incl. Nov additions), `src/corpus/` (schema,
  RLS, profile, `bug_seeds/` = the 9 reported bugs as seeds), `src/known_bugs/known_bugs.yaml` (the 9 bugs).
- Configs: `src/configs/rq1.yaml`, `rq3.yaml`, `rediscover.yaml` (all 9 bugs rediscovered in 150 s),
  `hunt_newest.yaml` (newest master hunt).
- Scripts: `scripts/setup_env.sh` (build PostgreSQL), `scripts/rediscover_servers.sh start N | restart W | stop N`
  (env `PGBIN`, `PGDATA_ROOT`; ports 5460+w; runs as user `pg`).
- Results: `runs/memberA-rq3/`, `runs/memberB-rq1-llm/` (campaign data), `triage/verdicts.yaml`
  (all 93 candidates decided: 8 real, 15 duplicate, 41 FP, 1 not-a-bug, 28 flaky, 0 open),
  `docs/RESULTS_ANALYSIS.md` (single source of numbers), `docs/evidence/rediscovery/`.
- Paper: `paper/` (acmart, 12 pages main text, `make`, `sh scripts/check.sh`; tables from
  `paper/scripts/make_tables.py`). Remaining paper blockers: `\todo` in the AI statement and
  `\num{anonymous mirror URL}` in `sections/data.tex` (owner decisions).
- Slides: `docs/final/` (final presentation 12 Nov: PPTX + PDF + SPEAKER_NOTES.md, built by
  `build_final.js` with pptxgenjs), `docs/meeting2/deck/` (meeting-2 deck).

## 4. Environment on the old machine (to recreate on a new laptop)

- PostgreSQL builds under `~/pgfuzz/install/{base,latest,newest,REL_18_STABLE}` from
  `~/pgfuzz/src/...`: `base` = master 26bd08fb (cassert; the build the paper's runs and the
  rediscovery use), `latest` = 126976a8, `newest` = 633dee1b (cassert), `REL_18_STABLE` = 18.6.
  Rebuild with `scripts/setup_env.sh` and checkout the commit you need
  (`./configure --prefix=... --enable-cassert --enable-debug --without-icu --without-readline --without-zlib`).
- initdb/servers must run as a non-root user (`useradd -m pg`).
- PostgreSQL builds are **not needed** any more (PostgreSQL hunting is finished).
- Python: `pip install -r src/requirements.txt` plus `duckdb --pre` (nightly 2.1.0.dev) and
  `datafusion` (55) for the generalized branch. Node + `pptxgenjs@3.12.0` and LibreOffice only for slides.

## 5. The new work: generalization (branch `generalized`)

Plan: `docs/generalized/PLAN.md` (targets, tasks G1–G10, paper claims). Summary of tasks:

Tasks G1–G11 with acceptance criteria, improvisation ideas and the paper's claims are in
PLAN.md; follow it and keep its Status column current. Bug campaigns produce filing packages only
(section 1d); the owner files them.

### State of G3 (DuckDB), exactly where it stopped

Committed in this hand-off commit (new files):
- `src/pgfuzz/targets/duckdb_executor.py`: `DuckDBExecutor` — in-memory DuckDB inside a spawned worker
  process (crash isolation: a dead worker = crash with exit code; a timeout kills the worker), per-test-case
  transaction (DuckDB has no savepoints: on error it rolls back and replays the successful statements),
  DuckDB exception class → pseudo SQLSTATE (`InternalException`/`FatalException` → XX000), plan variants =
  `PRAGMA disable_optimizer`, `SET threads=1`, or one `SET disabled_optimizers='<name>'` from
  `duckdb_optimizers()`, metamorphic checks like the PostgreSQL executor (cert/rls skipped).
- `src/corpus/duckdb/schema.sql` + `schema.yaml` (PostgreSQL schema minus partitions, inheritance,
  ranges, RLS; `CREATE TYPE jsonb AS JSON`).
- `src/configs/duckdb.yaml` (Grammar+Oracles on DuckDB, still using `grammar/postgres.pgg`),
  `src/known_bugs/duckdb.yaml` (empty).

It runs: `cd src && python -m pgfuzz -q sample configs/duckdb.yaml -n 300 --execute --seed 1 --out /tmp/x`.
First measurement (300 test cases, 992 statements) — **validity is still poor**; top errors:
1. `Parser Error: syntax error at or near "?"` (336): the PostgreSQL jsonb `?` operator; DuckDB has no `?`.
2. Unnamed `CREATE INDEX ON ...` (DuckDB needs a name), `SET LOCAL` (not implemented),
   `EXPLAIN (COSTS OFF / VERBOSE)`, `int4range` literals/type, `jsonb_*` functions, `@@` jsonpath,
   `ON CONFLICT` without a unique key, `n1`/`n2` tables created by unsupported DDL.

**Next steps (do these in order):**
1. **Dialect overlay mechanism (G2):** the grammar DSL can only *add* alternatives today (fragments are
   appended; rules with the same name accumulate). Add an overlay file format, e.g. directives in a
   `.pgg` overlay: `%drop <rule> "<substring of the alternative text>"`, `%droptype <type>`, and normal rules
   to add alternatives. Simplest implementation: keep each `Alt`'s source text (the parser knows the line)
   and filter in `parse_grammar`/`_load_grammar` before `_resolve`. Then write `grammar/duckdb.overlay.pgg`:
   drop the jsonb `?`/`?|`/`?&`/`@@`/`@?` alternatives, jsonb_* functions (or map to `json_*`), int4range,
   `SET LOCAL ...` (replace by nothing; DuckDB settings are session-wide), `EXPLAIN (...)` options, unnamed
   CREATE INDEX (use `@fresh_name`), partition/inheritance/RLS/policy DDL, `CREATE STATISTICS`,
   `pg_restore_extended_stats`, user-defined casts; add DuckDB features (LIST/STRUCT/MAP functions,
   `QUALIFY`, `ASOF JOIN`, `POSITIONAL JOIN`, `PIVOT/UNPIVOT`, `SUMMARIZE`, `GROUP BY ALL`, `list_*`,
   lambda functions, `UNNEST(recursive)`, window `EXCLUDE`, `FILTER`, `ARG_MAX`, `ANY_VALUE`, sampling
   `USING SAMPLE` (exclude from oracles: nondeterministic), `DISTINCT ON`, `string_agg ORDER BY`).
   Goal: ≥95 % validity in `sample --execute`.
2. Add `--grammar-overlay` / config param `overlays:` to `GrammarGenerator`.
3. Run a DuckDB campaign: `python -m pgfuzz run configs/duckdb.yaml -j 4` (check `results/duckdb/`),
   triage candidates (`pgfuzz triage configs/duckdb.yaml <failure dirs>`), validate on the newest nightly
   (`pip install --pre -U duckdb`), duplicate-search https://github.com/duckdb/duckdb/issues, then write
   a filing package as in section 1d (`docs/bughunt/duckdb/D-NN-<slug>/`; DuckDB repo:
   https://github.com/duckdb/duckdb, CONTRIBUTING requires tests in `test/sql/`). Do not file it.
   DuckDB wrong-result oracles: TLP/NoREC/expression rewrites and optimizer-off variants are the strongest;
   be careful with floating-point aggregates (masking exists), `ORDER BY` ties, `LIMIT` without total order,
   `random()`, `USING SAMPLE`, threads (row order), and DuckDB's documented semantic differences.
4. Unit tests for the DuckDB executor (spawn a worker, crash detection with a deliberate abort is hard;
   at least: error mapping, digest, variants, checks) — keep `pytest` green.
5. DataFusion (G4): building `datafusion-cli` from `main` with cargo was blocked in the previous
   session (it runs external build scripts). Try it in your session
   (`git clone --depth 1 https://github.com/apache/datafusion && cd datafusion && cargo build -p datafusion-cli`);
   if it is still blocked, note it in PROGRESS.md and start with the `datafusion` pip package (release 55).
   DataFusion bugs: https://github.com/apache/datafusion/issues (filing is the owner's).
6. Then G5/G6/G8/G10 as in PLAN.md. For the paper: new framing "typed derivation trees + oracles that
   transfer across SQL engines + engine-gated LLM grammar extension"; RQs across ≥3 engines; compare with
   SQLancer (supports PostgreSQL, DuckDB, SQLite, DataFusion) under the same budget.

## 6. Other pending items for the course (before 13 Nov) — the owner's items; act only if he asks

- P1 Record E-02's bug number when the owner gives it (E-02 md, RESULTS_ANALYSIS, slides, paper table, verdicts).
- P2 Paper `sections/data.tex`: AI-use statement (`\todo`) — owner's decision; anonymous mirror URL (`\num{}`)
  — owner must create (anonymous.4open.science). Then `cd paper && make && sh scripts/check.sh` must pass,
  main text ≤ 12 pages (check: references start on page 13 at most; conclusion ends on page 12).
- P3 Paper/slides could add E-01 (#19826) and E-02 to the bug table once numbers are confirmed (keep 12 pages).
- P4 Publish to the professor's repo: the owner uses another tool ("Antigravity") with a prompt already given:
  clone `main` into a fresh clone, `git filter-repo` to strip commit trailers and "Claude/Anthropic/AI assistant"
  prose (excluding `paper/` and the LLM client code), then merge into
  https://github.com/PASS-IITG/cs5187-term-project-blazing-bhuvi with `git merge --allow-unrelated-histories -s ours`
  so the target keeps its history and its tree equals cleaned `main`; plain push, no force. (No access to that
  repo from the old session.)
- P5 Final presentation (12 Nov) is in `docs/final/`; Gowtham may add 3 slides about his bugs.
- P6 Teams post with all bugs (owner has the text; needs the missing links listed in section 2).

## 7. Gotchas learned the hard way

- `pkill -f <pattern>` kills your own shell when the pattern is in the command line. Kill by PID:
  `ps -eo pid,args | awk '$2 ~ /python/ && /hunt_newest/ {print $1}' | xargs -r kill`.
- `pgfuzz run` uses multiprocessing; killing the parent leaves **orphaned workers** that keep fuzzing the same
  servers (they hold locks → statement timeouts → hang-oracle restarts → fake "crash" candidates). After
  stopping a run: `ps -eo pid,args | awk '$2=="/usr/bin/python" && /multiprocessing/ {print $1}' | xargs -r kill -9`.
- The hang oracle restarts a server only if a statement is still running 5 s after the cancel (fixed).
- Crash recovery can fail with "could not create file … File exists" (upstream #17731): re-init that cluster
  (`rm -rf /home/pg/rd-N && scripts/rediscover_servers.sh start N+1`).
- The IGNORE NULLS frame alternative triggers the known hang (AUDIT-F2) often; its weight is 0.05.
- A build installed while a WIP patch was in the tree poisons results (happened with `install/latest`):
  build patched trees into a separate prefix or `DESTDIR`, never into the evaluation installs.
- The session's network could not reach postgresql.org (archives); GitHub and pip worked.
- Long commands: run in the background and wait on a file/condition; don't sleep in loops.

## 8. How to start (for the next session)

1. Clone and create your public repo as in section 1b.
2. Read this file, `docs/generalized/PLAN.md`, `docs/RESULTS_ANALYSIS.md`.
3. `cd src && pip install -r requirements.txt && pip install --pre -U duckdb && python -m pytest -q` (151 pass).
4. Continue at section 5 "Next steps", step 1 (dialect overlay), and push after each step.
5. Create your public repository (section 1b), continue `docs/generalized/PROGRESS.md`, push.
6. Do not wait for answers: open decisions go into PROGRESS.md (placeholders), work continues.
