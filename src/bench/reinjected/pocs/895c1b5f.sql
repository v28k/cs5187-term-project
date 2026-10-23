CREATE TABLE rb_i4 (f1 int4);
INSERT INTO rb_i4 VALUES (0),(123456),(-123456),(2147483647),(-2147483647);
ANALYZE rb_i4;
CREATE TABLE rb_tk (unique1 int, unique2 int, two int, four int, ten int, hundred int);
INSERT INTO rb_tk SELECT i, (i*7919) % 10000, i % 2, i % 4, i % 10, i % 100 FROM generate_series(0, 9999) i;
CREATE INDEX rb_tk_u1 ON rb_tk(unique1); CREATE INDEX rb_tk_u2 ON rb_tk(unique2);
ANALYZE rb_tk;
SET from_collapse_limit = 1;
SELECT count(*) FROM rb_i4 t1,
  LATERAL (SELECT * FROM rb_tk t2,
           LATERAL (SELECT t2.ten AS x OFFSET 0) s0
           JOIN rb_tk t3 ON t3.unique2 = t1.f1
           WHERE t3.unique1 = t2.hundred + s0.x) ss1;
