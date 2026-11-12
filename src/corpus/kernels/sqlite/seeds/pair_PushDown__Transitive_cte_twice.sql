-- composition of rule kernels PushDown x Transitive (sqlite), template cte_twice
CREATE TABLE t(id INTEGER PRIMARY KEY, f TEXT UNIQUE);
INSERT INTO t VALUES (1, 'a'), (2, 'b');
WITH ka AS (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)), kb AS (SELECT CAST(' ' AS TEXT) AS c0, a1.n AS c1, CAST(42.5 AS NUMERIC) AS c2, a1.c0 AS c3 FROM v0 AS a1 WHERE ((UNICODE (CAST(' ' AS TEXT)) + 0) < a1.c0)) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) + (SELECT count(*) FROM ka);
-- pgfuzz:check kernel:cte_twice SELECT 2 * (SELECT count(*) FROM (SELECT c.id FROM t a JOIN t b ON a.f = b.f JOIN t c WHERE EXISTS (SELECT 1 FROM t d WHERE f = a.f AND f = c.f)) AS ka) + (SELECT count(*) FROM (SELECT CAST(' ' AS TEXT) AS c0, a1.n AS c1, CAST(42.5 AS NUMERIC) AS c2, a1.c0 AS c3 FROM v0 AS a1 WHERE ((UNICODE (CAST(' ' AS TEXT)) + 0) < a1.c0)) AS kb)
