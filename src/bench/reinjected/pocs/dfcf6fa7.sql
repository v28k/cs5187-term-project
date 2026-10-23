CREATE TABLE rb_tk (unique1 int, unique2 int, two int, four int, ten int, hundred int);
INSERT INTO rb_tk SELECT i, (i*7919) % 10000, i % 2, i % 4, i % 10, i % 100 FROM generate_series(0, 9999) i;
CREATE INDEX rb_tk_u1 ON rb_tk(unique1); CREATE INDEX rb_tk_u2 ON rb_tk(unique2);
ANALYZE rb_tk;
SET enable_hashagg = off;
SELECT two FROM rb_tk t1 WHERE two = 1
INTERSECT ALL
SELECT four FROM rb_tk t2 WHERE four = 1
UNION
SELECT ten FROM rb_tk dummy WHERE 1 = 2;
