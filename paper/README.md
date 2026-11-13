# Paper

[`paper.pdf`](paper.pdf) is the final paper: *Check the Tree: Finding Wrong Results in PostgreSQL with
Typed Derivation Trees and Commit-Directed Grammar Extension*, ACM Primary Article Template
(`sigconf`), 13 Nov 2026.

This folder holds its LaTeX source. Build and check it with:

```sh
cd paper
make          # builds main.pdf
make check    # LaTeX errors, undefined references, open items, banned words, page limit
```

`python3 paper/scripts/make_tables.py` (from the repository root) regenerates the tables from the
run data. [`HANDOFF.md`](HANDOFF.md) lists every number in the paper with the file it comes from;
[`STYLE.md`](STYLE.md) and [`CHECKLIST.md`](CHECKLIST.md) are the course's writing guide and
submission checklist.
