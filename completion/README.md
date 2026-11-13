# CS-5187 Term Project A3: completion package

**LLM-guided grammar-aware fuzzing of PostgreSQL** (tool `pgfuzz`, called **Arbor** in the paper),
and its generalization to DuckDB, SQLite, Turso and Apache DataFusion.
Team: **Venu Kummari, Bhuvan Chilukuti, Gowtham Reddy** (IIT Guwahati). License: MIT.

## Contents

| File | What it is |
|---|---|
| [`paper.pdf`](paper.pdf) | the paper, ACM Primary Article Template (`sigconf`), 9 pages: motivation, technique, implementation, evaluation (4 RQs), discussion (incl. the generalized fuzzer), threats to validity, related work, data availability, use of generative AI, **signed statement of contributions** |
| [`paper_source.zip`](paper_source.zip) | the LaTeX source of the paper for Overleaf (New Project -> Upload Project; compiles as is with pdfLaTeX + BibTeX) |
| [`complete_project_document.pdf`](complete_project_document.pdf) | the complete project document (61 pages): every component, every result, every bug with its state, the generalized fuzzer, contributions, deliverables, reproduction, questions and answers |
| [`slides/final_presentation.pdf`](slides/final_presentation.pdf), [`.pptx`](slides/final_presentation.pptx) | final presentation (Beamer, 24 slides) and its editable PowerPoint version (same design): architecture and techniques of the PostgreSQL fuzzer and of the generalized fuzzer, evaluation, how the tool found each bug; [speaker notes](slides/final_presentation_notes.pdf) |
| [`slides/class_talk.pdf`](slides/class_talk.pdf), [`.pptx`](slides/class_talk.pptx) | class talk (Beamer, 12 slides, about 7 minutes) and its editable version; [speaker notes](slides/class_talk_notes.pdf) |
| [`slides/slides_source.zip`](slides/slides_source.zip) | LaTeX (Beamer) source of both decks, for Overleaf |
| [`classtalk/`](classtalk/README.md) | **short class talk (5–6 minutes, 9 slides)**: PDF, editable PowerPoint, speaker notes with timings, source |
| [`progress/`](progress/) | progress meeting 1 (report, slides) and progress meeting 2 (report, slides, 48-page study guide), as presented on their dates |
| [`LICENSE`](LICENSE) | MIT license of the repository |

## Course requirements and where each one is met

| Requirement | Where |
|---|---|
| Proposal (2 pages) | submitted by the team leader on the proposal form by 20 Sep 2026 |
| Progress meetings 1 and 2 | [`progress/`](progress/) |
| Final presentation (10–15 min) | [`slides/final_presentation.pdf`](slides/final_presentation.pdf) (Beamer; source `docs/presentation/`, `make`) |
| Paper in FSE format, ACM `sigconf`, Overleaf | [`paper.pdf`](paper.pdf), [`paper_source.zip`](paper_source.zip) |
| Each member's contribution: signed statement + commit history | last section of [`paper.pdf`](paper.pdf); commit history (GitHub users `v28k` = Venu Kummari, `Blazing-bhuvi` = Bhuvan Chilukuti, `doma2542` = Gowtham Reddy) |
| Public GitHub repository, permissive license | MIT ([`../LICENSE`](../LICENSE)) |
| `README.md` with build + run instructions and exact dependencies | [`../README.md`](../README.md), [`../src/requirements-lock.txt`](../src/requirements-lock.txt) |
| One-command reproduction of the headline result | `sudo bash scripts/reproduce.sh` -> "Known bugs reproduced: 9 of 9" (tested 9 Nov 2026) |
| Bug reports / PRs / patches filed upstream, with their state | table below and [`../README.md`](../README.md); reproducers and patches in [`../docs/bughunt/`](../docs/bughunt/) |
| A bug accepted by upstream maintainers | **nine PostgreSQL bugs fixed upstream, six of them with our patches**; DuckDB fix approved by a maintainer |

## Upstream reports and their state (13 Nov 2026)

PostgreSQL (eleven bugs found by the tool and reported):

| Bug | Report | State |
|---|---|---|
| parallel `Append` assertion | [BUG #19803](https://postgr.es/m/19803-1fcc1df108c54ab6@postgresql.org) | **merged**: `abda2a2c` (David Rowley), back-patched to 14 |
| `to_char()` NUL byte, breaks `NORMALIZE` | [BUG #19771](https://www.postgresql.org/message-id/19771-4f173b891525020c@postgresql.org) | **merged**: our patch, `776df8a6` (Tom Lane) |
| duplicate statistics expression assertion | [pgsql-bugs](https://www.postgresql.org/message-id/PN0P287MB0903563C70D8E5B81912E855A7602@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, `b0392c26` (David Rowley), back-patched to 14 |
| `JSON_TABLE` assigns no collations | [BUG #19768](https://www.postgresql.org/message-id/19768-3633daa830be95db@postgresql.org) | **merged**: our patch, [`e405a46c`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=e405a46c45) (Amit Langote), back-patched to 17 |
| `NOT IN` anti-join ignores an implicit cast | [pgsql-bugs](https://www.postgresql.org/message-id/PN0P287MB090375874C6D5433282EC9DFA7642@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, [`b7eee09e`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=b7eee09eab) (Richard Guo) |
| `IGNORE NULLS` frame never returns | [pgsql-bugs](https://www.postgresql.org/message-id/PN0P287MB09038F3BD9921EBACF5646F6A7632@PN0P287MB0903.INDP287.PROD.OUTLOOK.COM) | **merged**: our patch, [`69b20fdd`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=69b20fdd20) (Tatsuo Ishii) |
| `MERGE`: SubPlan with no parent | [BUG #19802](https://www.postgresql.org/message-id/19802-ef50a8f1a4b5deee@postgresql.org) | **merged**: `7a5559a6` (Tender Wang, committed by Dean Rasheed), back-patched to 15 |
| `range @> NULL` folded to a constant | [BUG #19793](https://www.postgresql.org/message-id/19793-16d3a1bf33dff0fb@postgresql.org) | **open**: reported with a patch |
| non-finite imported MCV frequencies | pgsql-hackers ([patch](../docs/bughunt/bhuvan/patches/0001-Reject-non-finite-MCV-frequencies-in-pg_restore_exte.patch)) | **open**: patch submitted |
| `corr()`/`regr_*()` of a constant input under partial aggregation | [BUG #19826](https://postgr.es/m/19826-4b769cb5342fdfe7@postgresql.org) | **merged**: our patch, [`ef1b7404`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=ef1b740441) (Tom Lane), back-patched to 19 |
| Memoize: "plan should not reference subplan's variable" | BUG #19828 (with our patch) | **fixed**: [`45ff0b4a`](https://git.postgresql.org/gitweb/?p=postgresql.git;a=commit;h=45ff0b4a31) (Richard Guo, for a separate report of the same error) |


Generalized fuzzer (branch `generalized` of <https://github.com/v28k/cs5187-term-project>), each filed with a fix and a regression test:

| Engine | Bug | Issue / PR | State |
|---|---|---|---|
| Turso | `percentile_disc`/`percentile_cont` with an expression argument | [#11594](https://github.com/tursodatabase/turso/issues/11594) / [#11595](https://github.com/tursodatabase/turso/pull/11595) | **open** (in review) |
| DuckDB | `min`/`max` over a nested value computed by a subquery | [#28551](https://github.com/duckdb/duckdb/issues/28551) / [#28552](https://github.com/duckdb/duckdb/pull/28552) | **approved** (auto-merge enabled by a maintainer, 2.0 backport) |
| DataFusion | `UPDATE`/`DELETE` repeating an expression (`__common_expr_1`) | [#27235](https://github.com/apache/datafusion/issues/27235) / [#27236](https://github.com/apache/datafusion/pull/27236) | **open** (validated by a contributor) |
| Turso | aggregate in `IN (SELECT ...)` next to a window function (misuse error or panic) | [#11796](https://github.com/tursodatabase/turso/issues/11796) / [#11797](https://github.com/tursodatabase/turso/pull/11797) | **open** (filed 13 Nov) |

Also filed on 13 Nov: DataFusion DF-02 (scalar subquery inside `VALUES`), with a fix.
