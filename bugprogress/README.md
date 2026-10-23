# Hunter C bug-hunt progress

- `C-progress.md`: full progress report (environment, confirmed bug, candidates, untested ideas, checks done)
- `C-01-dependencies-duplicate-expression-assert.md` / `.sql` / `.patch`: the one confirmed new bug, ready to file
- `scripts/`: the differential test scripts used (Python + psycopg; argument 1 = port, argument 2 = seed where applicable)
  - `binrt.py` binary I/O round trip, `numfloat.py` numeric vs float8, `winagg.py` window aggregates vs subqueries,
    `xmlrt.py` xml binary round trip, `raw2x.py` raw-parse-tree double analysis, `xstats.py`/`xstats2.py` extended statistics fuzzer

# Hunter B bug-hunt progress

- `B-progress.md`: full progress report (environment, confirmed bug, duplicate, untested candidates B-u-1..8, features audited)
- `B-01-full-join-notnull-folding.md` / `.sql` / `.patch`: the one confirmed new bug, ready to file (PG19 regression)
- `scripts/B_h.py`, `scripts/B-fz1.py`, `scripts/B-fz2.py`: differential fuzzers (master 5433 vs 18.6 5435), `scripts/B-dup19765-variants.sql`: variants of the duplicate BUG #19765
