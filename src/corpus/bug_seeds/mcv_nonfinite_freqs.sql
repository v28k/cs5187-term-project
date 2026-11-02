-- Extended statistics (pgsql-hackers patch, Oct 2026): pg_restore_extended_stats()
-- accepts NaN and Infinity in most_common_freqs, after which the planner
-- estimates 1e100 rows for a 1000-row table. Affected: master. Detected by the
-- CERT check: adding the WHERE clause must not raise the row estimate.
CREATE TABLE mcvt (a int, b int);
INSERT INTO mcvt SELECT x % 2, x % 2 FROM generate_series(1, 1000) x;
CREATE STATISTICS mcvt_s (mcv) ON a, b FROM mcvt;
ANALYZE mcvt;
SELECT pg_restore_extended_stats('schemaname', 'public', 'relname', 'mcvt', 'statistics_schemaname', 'public', 'statistics_name', 'mcvt_s', 'inherited', false, 'most_common_vals', '{{0,0},{1,1}}'::text[], 'most_common_freqs', '{NaN,0.3}'::double precision[], 'most_common_base_freqs', '{0.1,0.1}'::double precision[]);
SELECT * FROM mcvt WHERE a = 0 AND b = 0;
-- pgfuzz:check cert SELECT * FROM mcvt
