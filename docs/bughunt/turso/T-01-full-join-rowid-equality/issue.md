> **Do not file: fixed upstream (see report.md). Kept for the record.**

**Title:** FULL OUTER JOIN on an INTEGER PRIMARY KEY column: "requires an equality condition in the ON clause"

```sql
CREATE TABLE t (a INTEGER, b TEXT);
CREATE TABLE u (a INTEGER PRIMARY KEY, b TEXT);
INSERT INTO t VALUES (1, 'x'), (2, 'y');
INSERT INTO u VALUES (1, 'p'), (3, 'q');
SELECT * FROM t FULL JOIN u ON t.a = u.a;
-- Parse error: FULL OUTER JOIN requires an equality condition in the ON clause
```

The condition is an equality. The same query works when `u.a` is a plain INTEGER column (not the rowid alias).
Expected (SQLite 3.54.1): `(1, 'x', 1, 'p')`, `(2, 'y', NULL, NULL)`, `(NULL, NULL, 3, 'q')`.

Version: pyturso 0.8.3 (Linux x86_64). Found with a grammar-based SQL fuzzer comparing Turso with SQLite.
