-- pgfuzz triage of 2a82e01aba28: wrong_result via metamorphic:rls
-- the two queries below must return the same rows (as a multiset):
VALUES ((SQRT (ABS ((SELECT SUM (10.0::float8) FROM t4 AS a1 WHERE FALSE))) + (0)::float8), (10 + LENGTH (''::text)), (SELECT JSONB_AGG ((SELECT SUM (a3.c0) FROM t1 AS a3 WHERE TRUE) ORDER BY (SELECT SUM (a3.c0) FROM t1 AS a3 WHERE TRUE)) FROM t3 AS a2));
VALUES ((SQRT (ABS ((SELECT SUM (10.0::float8) FROM t4 AS a1 WHERE FALSE))) + (0)::float8), (10 + LENGTH (''::text)), (SELECT JSONB_AGG ((SELECT SUM (a3.c0) FROM t1 AS a3 WHERE TRUE) ORDER BY (SELECT SUM (a3.c0) FROM t1 AS a3 WHERE TRUE)) FROM (SELECT * FROM t3 WHERE (c1 IS NOT FALSE)) AS a2));
