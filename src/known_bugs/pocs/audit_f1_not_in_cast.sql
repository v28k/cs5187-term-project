-- AUDIT-F1 (pgsql-bugs, 23 Oct 2026): the NOT IN -> anti-join conversion
-- (commit 383eb21ebf) ignores an implicit cast on the sub-select side that can
-- turn a non-NULL value into NULL, so NOT IN returns rows instead of NULL.
-- Affected: 19rc1, master; not 18. Detected by TLP on WHERE: the three
-- partitions together return more rows than the original query.
CREATE TABLE f1o (t text NOT NULL);
CREATE TABLE f1s (i int NOT NULL);
INSERT INTO f1o VALUES ('1');
INSERT INTO f1s VALUES (0);
CREATE FUNCTION pgf_i2t(int) RETURNS text IMMUTABLE STRICT LANGUAGE sql AS $$ SELECT CASE WHEN $1 <> 0 THEN $1::varchar END $$;
CREATE CAST (int AS text) WITH FUNCTION pgf_i2t(int) AS IMPLICIT;
SELECT t FROM f1o WHERE t NOT IN (SELECT i FROM f1s);
-- pgfuzz:check tlp_where SELECT t FROM f1o WHERE (t NOT IN (SELECT i FROM f1s)) UNION ALL SELECT t FROM f1o WHERE NOT (t NOT IN (SELECT i FROM f1s)) UNION ALL SELECT t FROM f1o WHERE (t NOT IN (SELECT i FROM f1s)) IS NULL
