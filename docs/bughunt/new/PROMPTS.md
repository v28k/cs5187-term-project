# Prompts for parallel bug-hunting chats

Paste one prompt per new Claude Code chat (cloud session with the repository
`v28k/cs5187-term-project`). Each hunter uses a different method and its own
report prefix, so pushes never collide.

| Chat | Method | Prefix |
|---|---|---|
| 1 | Audit the source code of features added to master in the last months | `B-` |
| 2 | Recent pgsql-bugs reports: reproduce, mutate, find new bugs nearby | `C-` |
| 3 | Review the diffs of the newest commits (last 4 weeks) line by line | `D-` |
| main chat | Pattern hunt: code with the same bug pattern as BUG-01/BUG-02 | `E-` |
| (already running) | Hunter A: mutate the 23 recently fixed benchmark bugs | `A-` |

---

## Common part (included in every prompt below)

```
CONTEXT
You are a bug hunter for our CS-5187 project "LLM-guided grammar-aware fuzzing of
PostgreSQL" (repository v28k/cs5187-term-project, branch main). Read first, quickly:
docs/bughunt/BUG-02-range-containment-null.md (our model report: a silent wrong
result in a planner support function), docs/bughunt/BUG-01-json_table-collation.md,
docs/bughunt/new/README.md (report format), docs/bughunt/new/main-notes.md (what
was already checked). Goal: find NEW, previously unknown PostgreSQL bugs that
upstream will accept, as fast as possible, and push one complete report per bug.
Known and excluded: BUG-01, BUG-02, the 23 fixes in src/bench/reinjected/bugs.yaml.

SETUP (start it first, read code while it builds; ~25 min on 4 cores)
  bash scripts/setup_env.sh > /tmp/setup.log 2>&1 &     # master (cassert) + REL_18
Then start two servers as the unprivileged user pg (create it with useradd -m pg
if missing; initdb refuses root):
  for v in master:5433 REL_18_STABLE:5435; do b=${v%%:*}; p=${v##*:}; d=/home/pg/d$p
    su pg -c "$HOME/pgfuzz/install/$b/bin/initdb -D $d -U postgres -A trust >/dev/null &&
      echo \"port=$p\" >> $d/postgresql.conf &&
      $HOME/pgfuzz/install/$b/bin/pg_ctl -D $d -l $d/postgresql.log start"; done
(If $HOME/pgfuzz/install is not where setup_env.sh installed, check its ROOT variable.)
Assertion failures appear as "TRAP:" lines in /home/pg/d5433/postgresql.log.
The master clone is $HOME/pgfuzz/src/postgres-master (git log, git show, grep there).
Before writing a report, fetch the newest master (git fetch --depth=200 origin master)
and check the bug is not already fixed (git log FETCH_HEAD --grep / read the code).

ORACLES (how to decide something is a bug)
- crash or assertion failure (TRAP) on the cassert build;
- internal error, SQLSTATE XX000 ("should not happen" messages);
- wrong result: the same query gives different rows under different planner settings
  (SET enable_hashjoin/mergejoin/nestloop/hashagg/seqscan/indexscan = off,
  work_mem='64kB', parallel query forced, jit), or differs from an equivalent
  query (e vs (SELECT e), WHERE p split into p / NOT p / p IS NULL, count(*) WHERE p
  vs sum(CASE WHEN p THEN 1 ELSE 0 END)), or differs from 18.x where the documented
  semantics did not change;
- a result that contradicts the documentation or the SQL standard.
Not bugs: LIMIT/OFFSET without total ORDER BY, volatile functions, row order without
ORDER BY, float summation order, intended changes listed in the release notes.
Script mass testing in Python with psycopg rather than one psql call at a time.

VERIFY BEFORE REPORTING (mandatory)
- reproduce >= 3 times on a fresh database with a minimal self-contained script
  (its own CREATE TABLE / INSERT), reduced to the smallest form;
- run it on master (cassert), on 18.x, and say which versions are affected;
- explain why the expected result is right (docs section, standard, or an
  equivalent query PostgreSQL answers differently);
- find the root cause in the source (file, function, code excerpt) and propose a
  fix; write a patch and run the relevant regression test if it is cheap;
- duplicate check: newest master git log, and a search of pgsql-bugs.
Be strict: one solid report is worth more than five doubtful ones. Doubtful
findings go to docs/bughunt/new/<PREFIX>candidates.md.

REPORT AND PUSH (immediately after each confirmed bug)
docs/bughunt/new/<PREFIX>NN-<short-slug>.md (NN = 01, 02, ...) with: status,
summary, minimal reproducer, actual vs expected and why, versions, root cause, fix
or patch, how found and how verified (commands, counts), duplicate check, draft
text for https://www.postgresql.org/account/submitbug/ . Put .sql and .patch files
next to it with the same prefix. Then:
  git add <your files only>
  git -c user.name=v28k -c user.email=samruddhi.sonawane6116@gmail.com commit -m "..."
  git pull --rebase origin main && git push origin main   (retry on failure; other
  hunters push to the same branch)
Keep hunting after each push. At the end, reply with the list of reports
(path, one line, confidence) and candidates.
```

---

## Prompt 1: audit the source code of new features (prefix `B-`)

```
<paste the common part here>

YOUR METHOD (prefix B-): audit the source code of features added to PostgreSQL
master since mid-2025 (PG 19 and 20devel), especially in the optimizer and
executor. Find them with git log --since=2025-07-01 --stat -- src/backend/optimizer
src/backend/executor src/backend/utils/adt src/backend/parser, and with the release
notes draft / regression tests changed recently (git log -- src/test/regress/sql).
Candidates: eager aggregation (enable_eager_aggregate), NOT NULL based
simplification (expr_is_nonnullable and its callers), self-join elimination
(analyzejoins.c), OR-to-ANY transformation, btree skip scan, virtual generated
columns, GROUP BY/DISTINCT key reordering, hash join handling of NULL keys
(1811f1af9, 126976a8), Memoize, partitionwise changes, new SQL functions and syntax.
For each feature: read the code, write down every assumption it relies on
(non-null, uniqueness, type or collation equality, strictness, volatility,
outer-join nullability, cross-type operators, NaN/-0/Infinity, empty input,
inheritance/partitions, generated columns, RLS, prepared generic plans), then write
SQL that breaks exactly that assumption and compare results with the feature on vs
off (its enable_* setting, or an equivalent query the feature cannot apply to) and
against 18.x. Spend your time on the features with the most complex code and the
newest commits; move on quickly when a feature looks solid.
```

## Prompt 2: recent pgsql-bugs reports, mutate and find neighbours (prefix `C-`)

```
<paste the common part here>

YOUR METHOD (prefix C-): start from recent bug reports. Read the pgsql-bugs list
archive for the last 6-8 weeks (https://www.postgresql.org/list/pgsql-bugs/ , by
month; use WebFetch) and the commits that fixed bugs in that period (git log
--since=2026-08-15 --grep=Fix --grep=bug -i on newest master). Pick reports about
the planner, executor, SQL functions, JSON, ranges, collations, partitions and
wrong results. For each:
(a) if it is still open or unconfirmed: reproduce it on master and 18.x; if it is
    real and nobody has confirmed or fixed it, analyse the root cause and write a
    report that adds what the thread lacks (minimal reproducer, versions, root cause,
    patch) - note in the report that it was first reported by <author, link>, and
    never present someone else's bug as ours;
(b) mutate it to find NEW bugs nearby: the same mistake usually exists in sibling
    code. Change the data types (numeric, float NaN/-0/Infinity, text with
    collations, ranges, jsonb, arrays, domains), the join type (LEFT/FULL/LATERAL/
    semi/anti), the nesting (subquery, CTE, view, set operation), the table kind
    (partitioned, inheritance, generated columns, RLS), and planner settings; and
    grep the source for code written the same way as the fixed code (same helper,
    same copy-pasted pattern) and test each site.
A finding in (b) that differs from the original report is a new bug: report it
with its own prefix C-NN.
```

## Prompt 3: review the newest commits line by line (prefix `D-`)

```
<paste the common part here>

YOUR METHOD (prefix D-): code review of the newest master commits, newest first.
git fetch --depth=400 origin master; then for every commit of the last 4 weeks that
touches src/backend (git log --since=2026-09-25 --format='%h %ad %s' FETCH_HEAD --
src/backend), read the full diff (git show) like a reviewer: what invariant does
the change rely on, which callers or cases did it not consider (NULL inputs,
empty sets, multi-batch / parallel / rescan paths, outer joins, partitions,
prepared generic plans, error paths, cross-type operators, collations, overflow,
other node types the switch statements miss). For each suspicion, write SQL that
reaches the changed lines (start from the regression test the commit added and
mutate it), and test it with the oracles. Commits that fix a bug often fix only
one of several similar call sites: grep for the other sites and test them.
Regressions in unreleased master code are fixed fastest upstream ("open items"),
so prefer those. Today's newest commit is 126976a8 (hash join null-keyed outer
tuples); main-notes.md lists what was already checked for it.
```
