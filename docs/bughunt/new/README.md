# Bug hunt 2 (23-24 Oct 2026): new candidates

Parallel hunt, one hunter per method. Every confirmed bug gets one report file
`<ID>-<slug>.md` here; uncertain findings go to `<hunter>-candidates.md`.

| Hunter | Method | Server (master 26bd08fb, cassert) |
|---|---|---|
| A | mutate the 23 recently fixed bugs (incomplete fixes, siblings) and recent unresolved pgsql-bugs reports | 5471 |
| B | read the code of recent master features (eager aggregation, NOT NULL simplification, self-join elimination, OR-to-ANY, skip scan, virtual generated columns, ...) and test them differentially | 5472 |
| C | siblings of BUG-01/BUG-02: planner support functions with NULL/edge inputs (e vs (SELECT e)), missing collation assignment in other parse paths | 5473 |
| campaigns | grammar + all oracles + cross-version, 8 h, two servers (`configs/hunt2a.yaml`, `hunt2b.yaml`) | 5434, 5460 |

Reference: PostgreSQL 18.6 on 5435. Newest master (cassert) on 5474 once built.

## Report format (each file)

1. Status line (confirmed / root-caused / patch written / not filed)
2. One-paragraph summary
3. Minimal reproducer (copy-paste SQL, self-contained)
4. Actual vs expected, and *why* the expected result is right (docs, SQL standard, or an equivalent query)
5. Versions: master 26bd08fb (cassert), 18.6, newest master (if built), 17 if known
6. Root cause (file, function, code excerpt)
7. Suggested fix (patch if feasible)
8. How found, how verified (reproductions, fresh database, plan, commands)
9. Duplicate check (git log of newest master, pgsql-bugs search)
10. Draft text for the pgsql-bugs form
