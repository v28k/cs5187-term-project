CREATE TABLE rb_tk (unique1 int, unique2 int, two int, four int, ten int, hundred int);
INSERT INTO rb_tk SELECT i, (i*7919) % 10000, i % 2, i % 4, i % 10, i % 100 FROM generate_series(0, 9999) i;
CREATE INDEX rb_tk_u1 ON rb_tk(unique1); CREATE INDEX rb_tk_u2 ON rb_tk(unique2);
ANALYZE rb_tk;
SELECT pct, count(unique1) FROM
  ((VALUES (0)) v(pct) FULL JOIN (VALUES (100)) w(pct) USING (pct)),
  LATERAL (SELECT * FROM rb_tk TABLESAMPLE bernoulli (pct)) ss
  GROUP BY pct ORDER BY pct;
