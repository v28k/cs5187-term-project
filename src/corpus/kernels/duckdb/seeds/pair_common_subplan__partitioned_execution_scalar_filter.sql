-- composition of rule kernels common_subplan x partitioned_execution (duckdb), template scalar_filter
SELECT count(*) FROM (SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1) AS ka WHERE (SELECT count(*) FROM (SELECT 1.0::float8 AS c0, '{"k": -1, "a": [1, 2, 3]}'::jsonb AS c1, a1.c0 AS c2, '2000-01-01'::date AS c3 FROM tl AS a1 WHERE NULLIF ((NOT COALESCE (FALSE, (EXISTS (SELECT FALSE AS c0)))), TRUE)) AS kb) >= 0;
-- pgfuzz:check kernel:scalar_filter SELECT count(*) FROM (SELECT DISTINCT 10::bigint AS c0, a1.c0 AS c1 FROM tl AS a1) AS ka
