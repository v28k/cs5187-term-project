-- BUG #19826: corr()/regr_r2()/regr_slope() of a constant input are NULL with a serial
-- plan but 1 when the aggregate is combined from partial states (partitionwise or
-- parallel aggregation). Found by the plan-variant oracle (variant partitionwise).
-- Regression from 649828769 on master; fixed by ef1b740441 (our patch). Reproduces on
-- the base build 26bd08fb.
CREATE TABLE e01 (k int, x float8) PARTITION BY LIST (k);
CREATE TABLE e01_1 PARTITION OF e01 FOR VALUES IN (1);
CREATE TABLE e01_2 PARTITION OF e01 FOR VALUES IN (2);
CREATE TABLE e01_3 PARTITION OF e01 FOR VALUES IN (3);
INSERT INTO e01 SELECT 1 + g % 3, 1.0 / 3 FROM generate_series(1, 80) g;
ANALYZE e01;
SELECT corr(x, x) AS c, regr_r2(x, x) AS r2, regr_slope(x, x) AS s FROM e01;
