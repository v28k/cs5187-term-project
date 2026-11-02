-- E-01: corr() / regr_r2() / regr_slope() of a constant input differ between
-- serial and partial (partitionwise or parallel) aggregation on master.
-- Self-contained; run with psql -X -f E-01-corr-partial-aggregate.sql
DROP TABLE IF EXISTS e01, e01p;
CREATE TABLE e01 (k int, x float8) PARTITION BY LIST (k);
CREATE TABLE e01_1 PARTITION OF e01 FOR VALUES IN (1);
CREATE TABLE e01_2 PARTITION OF e01 FOR VALUES IN (2);
CREATE TABLE e01_3 PARTITION OF e01 FOR VALUES IN (3);
INSERT INTO e01 SELECT 1 + g % 3, 1.0 / 3 FROM generate_series(1, 80) g;
ANALYZE e01;

-- serial: every x is the same value, so Sxx = 0 and the result is NULL
SET enable_partitionwise_aggregate = off;
SELECT corr(x, x), regr_r2(x, x), regr_slope(x, x) FROM e01;

-- partial aggregation per partition, combined by float8_regr_combine()
SET enable_partitionwise_aggregate = on;
EXPLAIN (COSTS OFF) SELECT corr(x, x) FROM e01;
SELECT corr(x, x), regr_r2(x, x), regr_slope(x, x) FROM e01;

-- the same through parallel query (several workers produce partial states)
RESET enable_partitionwise_aggregate;
CREATE TABLE e01p (x float8);
INSERT INTO e01p SELECT 1.0 / 3 FROM generate_series(1, 300000);
ANALYZE e01p;
SET max_parallel_workers_per_gather = 0;
SELECT corr(x, x), regr_r2(x, x), regr_slope(x, x) FROM e01p;
SET max_parallel_workers_per_gather = 4;
SET parallel_setup_cost = 0; SET parallel_tuple_cost = 0;
SET min_parallel_table_scan_size = 0;
EXPLAIN (COSTS OFF) SELECT corr(x, x) FROM e01p;
SELECT corr(x, x), regr_r2(x, x), regr_slope(x, x) FROM e01p;
