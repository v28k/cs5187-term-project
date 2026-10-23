SET enable_eager_aggregate = on;
CREATE TABLE rb_eas1 (a int2);
CREATE TABLE rb_eas2 (b int4, c double precision);
INSERT INTO rb_eas1 VALUES (5);
INSERT INTO rb_eas2 SELECT 5, 1 FROM generate_series(1, 100);
INSERT INTO rb_eas2 SELECT 65541, 1 FROM generate_series(1, 100);
ANALYZE rb_eas1, rb_eas2;
SELECT s1.a, sum(s2.c) FROM rb_eas1 s1 JOIN rb_eas2 s2 ON s1.a = s2.b GROUP BY s1.a;
