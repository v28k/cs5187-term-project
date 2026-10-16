# CS-5187 — Term Project

Project A3: **LLM-guided grammar-aware fuzzing of PostgreSQL**. Venu, Bhuvan,
and Gowtham.

We generate SQL, run it on an assert-enabled PostgreSQL built from source, and
compare three generators under the same time budget, schema, and oracle:

```text
Random/Mutation  ->  Grammar-only  ->  Grammar + LLM
```

The random arm builds a small SQL tree and then mutates the text. It does not
use the grammar. The grammar arm derives typed, scoped SQL and mutates the
derivation tree. The LLM arm is still planned: it will propose grammar rules
for recent PostgreSQL features, and a statement counts only after the server
runs it.

**Measured so far (16 October 2026).** PostgreSQL `20devel` at `d733fca`,
assertions on. Executor self-test 10/10. Unit tests: 65 when the harness and
grammar landed, 84 after the random baseline was added. Grammar samples of
300 test cases, seed 1: 83.4%, then 83.1%, then 88.4%, then **100%** (966 of
966 statements, 22.1 seconds, no errors). The differential oracle checked
230 queries in that last sample. Bug candidates so far: 0. The four-hour
campaigns have not started.

**From here.** Venu and Bhuvan follow features added recently in PostgreSQL
(MERGE, SQL/JSON, generated columns, partitions, new planner rewrites) and
point the grammar at that code. Bhuvan also reduces any bug candidate a run
prints. Gowtham keeps the comparison experiment, the statistics, the LLM arm,
and the paper. Meeting 2 is 26-30 October, meeting 3 is 2-6 November, the
presentation is 12 November, and the paper and repository are due 13 November.

The progress-meeting pack is in [`progressmeet1/`](progressmeet1/): slides
(PDF and PowerPoint), speaker notes, a handbook of the whole project, the
current-progress guide, and the plan through 13 November. Sources live in
[`docs/`](docs/).

How to run a short check, from `src/`, with the local servers already up:

```sh
python -m pgfuzz -q sample configs/local.yaml -n 300 --execute --seed 1 --out ../results/sample3
```

The long grammar hunt (two trials, four hours each) is
`python -m pgfuzz run configs/hunt.yaml -j 2 --no-plots`. Details, including
the server build, are in `progressmeet1/whole_project.pdf` and
[`src/README.md`](src/README.md).

---

This repository started from the CS-5187 term-project template. It has two
parts:

```
paper/    the report, in FSE (ACM acmsmall) LaTeX format  ← write here
src/      your code (tool, scripts, experiments, data)     ← code here
```

Your project can be in **any** area of the course: static analysis, dynamic
analysis / testing, or software engineering more broadly (empirical studies,
program repair, refactoring, build systems, …). The template does not assume a
particular topic.

## What to do

1. **Put your code in `src/`.** Everything that produces a result or a number in
   your paper goes there, with a note on how to build and run it. See
   [`src/README.md`](src/README.md).
2. **Write your report in `paper/`.** Edit the section files in
   `paper/sections/`. Build the PDF with:
   ```sh
   cd paper
   make          # builds paper/main.pdf
   make check    # checks for leftover TODOs, banned words, undefined refs, page limit
   ```
3. **Address the five graded parts.** In `paper/`, each is flagged with a red
   `FOCUS` box that says what it must contain. Write the section, then **delete
   that `\focus{...}` line** (keep the section). The graded parts are:

   | Part | Where |
   |------|-------|
   | Motivating example | `sections/introduction.tex` |
   | Workflow | `sections/approach.tex` |
   | Research questions | `sections/evaluation.tex` |
   | Related work | `sections/related.tex` |
   | Threats to validity | `sections/threats.tex` |

4. **Finish clean.** A submittable report has **zero** red `\focus` and **zero**
   `\todo`, and `make check` passes. Use
   [`paper/CHECKLIST.md`](paper/CHECKLIST.md) before you submit.

## Rules that matter (see `paper/STYLE.md`)

- Every number in the paper comes from a real run of your code in `src/` — never
  invented or rounded from memory.
- The motivating example must be **real**, with exact numbers.
- Cite only papers you have verified; fabricated citations are not accepted.
- Write in plain, simple English.

## Submitting

Commit both your `src/` code and your `paper/` sources (not the built PDF — it is
gitignored). Make sure the repository builds from a clean checkout:

```sh
cd paper && make
```
