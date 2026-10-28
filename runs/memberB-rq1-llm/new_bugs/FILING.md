# Filing N1 and N2 on pgsql-bugs

Same route as before (docs/bughunt/HANDOFF.md, "Filing steps"):

1. Sign in at https://www.postgresql.org/account/ (community account) and open
   **https://www.postgresql.org/account/submitbug/**.
2. File **one report per bug**. Fill the form fields from the boxes below
   (copy-paste the description as is).
3. Each report gets a number (BUG #19xxx) by email, and the thread appears on
   https://www.postgresql.org/list/pgsql-bugs/. Answer replies on that thread.
4. Tell the team the two bug numbers + thread URLs; they go into
   `triage/verdicts.yaml` (`upstream:`) and `docs/bughunt/LOG.md`.

Before submitting, open https://www.postgresql.org/list/pgsql-bugs/ and glance at
today's subjects for "MERGE" / "parallel_safe", in case someone sent it in the last hours.

---

## N1  (filed: BUG #19802, 28 Oct 2026)

| Form field | Value |
|---|---|
| PostgreSQL version | 18.6 |
| Operating system | Ubuntu 22.04 (WSL2), x86_64 |
| Short description | MERGE into a partitioned table fails with "SubPlan found with no parent plan" |

Description:

```
MERGE into a partitioned table fails with an internal error when the source is a
subquery that is not pulled up, an UPDATE SET clause contains a scalar subquery
that references the source, and the statement has both WHEN MATCHED UPDATE and
WHEN NOT MATCHED INSERT:

CREATE TABLE mp (a int, b text) PARTITION BY RANGE (a);
CREATE TABLE mp1 PARTITION OF mp FOR VALUES FROM (0) TO (10);
MERGE INTO mp t
USING (SELECT true AS c OFFSET 0) s ON t.a IS NULL
WHEN MATCHED THEN UPDATE SET b = (SELECT NULL WHERE s.c)
WHEN NOT MATCHED THEN INSERT VALUES (1, 'x');

ERROR:  SubPlan found with no parent plan

Reproduced on 17.11, 18.6 and master (4848fd675, 2026-10-28).

Each of these makes it succeed: a non-partitioned target table; dropping either
the WHEN MATCHED UPDATE or the WHEN NOT MATCHED INSERT action (or using DO NOTHING
instead of the INSERT); a join condition that references the source (ON true
also works); a source that is pulled up (no OFFSET/LIMIT); the equivalent
UPDATE ... FROM.

The same message was fixed for a SELECT case on a partitioned table in eacee6b61
("Don't use SubPlan-containing expressions for startup-time pruning"); that
commit is in the tested master, so this MERGE case seems to take a different path.

Found by a grammar-based SQL fuzzer (university course project); the script
above is the hand-reduced test case.
```

---

## N2

| Form field | Value |
|---|---|
| PostgreSQL version | 17.11 (also master) |
| Operating system | Ubuntu 22.04 (WSL2), x86_64; built with --enable-cassert |
| Short description | Assertion "!parallel_aware \|\| pathnode->path.parallel_safe" in create_append_path |

Description:

```
On an assert-enabled build this query crashes the backend:

CREATE TABLE pi (a int);
CREATE TABLE pi_child () INHERITS (pi);
WITH c1 AS (SELECT 1 FROM pi WHERE true UNION ALL SELECT 1 FROM pi WHERE false),
     c2 AS MATERIALIZED (SELECT 1)
SELECT 1 FROM c1 UNION ALL SELECT 2 FROM c2;

TRAP: failed Assert("!parallel_aware || pathnode->path.parallel_safe"),
File: "pathnode.c", Line: 1439   (master 4848fd675; line 1328 on 17.11)

Reproduced on 17.11 and master (4848fd675, 2026-10-28), default settings.
A release build (18.6) returns the expected rows.

Needed: an inheritance parent with a child (a plain table does not crash); the
inlined CTE being a UNION ALL with a constant-false branch (with only true
branches it does not crash); the outer UNION ALL including a MATERIALIZED CTE
scan. Writing the first branch as a FROM subquery instead of a CTE does not
crash. It looks like a parallel-aware Append is built although one of its
children is not parallel-safe.

Found by a grammar-based SQL fuzzer (university course project); the script
above is the hand-reduced test case.
```
