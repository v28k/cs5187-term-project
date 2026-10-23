SET enable_partitionwise_join = on;
SET enable_hashjoin = off;
SET enable_mergejoin = off;
CREATE TABLE rb_prt1 (a int, b int, c varchar) PARTITION BY RANGE (a);
CREATE TABLE rb_prt1_p1 PARTITION OF rb_prt1 FOR VALUES FROM (0) TO (250);
CREATE TABLE rb_prt1_p3 PARTITION OF rb_prt1 FOR VALUES FROM (500) TO (600);
CREATE TABLE rb_prt1_p2 PARTITION OF rb_prt1 FOR VALUES FROM (250) TO (500);
INSERT INTO rb_prt1 SELECT i, i % 25, to_char(i, 'FM0000') FROM generate_series(0, 599) i WHERE i % 2 = 0;
CREATE INDEX ON rb_prt1_p1 (a); CREATE INDEX ON rb_prt1_p2 (a); CREATE INDEX ON rb_prt1_p3 (a);
ANALYZE rb_prt1;
CREATE TABLE rb_prt2 (a int, b int, c varchar) PARTITION BY RANGE (b);
CREATE TABLE rb_prt2_p1 PARTITION OF rb_prt2 FOR VALUES FROM (0) TO (250);
CREATE TABLE rb_prt2_p2 PARTITION OF rb_prt2 FOR VALUES FROM (250) TO (500);
CREATE TABLE rb_prt2_p3 PARTITION OF rb_prt2 FOR VALUES FROM (500) TO (600);
INSERT INTO rb_prt2 SELECT i % 25, i, to_char(i, 'FM0000') FROM generate_series(0, 599) i WHERE i % 3 = 0;
CREATE INDEX ON rb_prt2_p1 (b); CREATE INDEX ON rb_prt2_p2 (b); CREATE INDEX ON rb_prt2_p3 (b);
ANALYZE rb_prt2;
SELECT t1.a, t1.c, t2.b, t2.c FROM rb_prt1 t1 LEFT JOIN
  (SELECT b, COALESCE(c, 'x') AS c FROM rb_prt2 WHERE a = 0) t2 ON t1.a = t2.b
  WHERE t1.c = t2.c ORDER BY t1.a, t2.b;
