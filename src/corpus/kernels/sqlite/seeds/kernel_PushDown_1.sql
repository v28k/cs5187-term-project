-- rule kernel: PushDown (sqlite)
SELECT CAST(' ' AS TEXT) AS c0, a1.n AS c1, CAST(42.5 AS NUMERIC) AS c2, a1.c0 AS c3 FROM v0 AS a1 WHERE ((UNICODE (CAST(' ' AS TEXT)) + 0) < a1.c0);
