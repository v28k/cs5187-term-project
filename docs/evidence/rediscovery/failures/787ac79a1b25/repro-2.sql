-- pgfuzz failure 787ac79a1b25 (performance, signature strength: message)
-- test case 1646 from grammar
-- SQLSTATE -: row estimate rises when the WHERE clause is added: 1000.0 -> 1e+100
-- failing statement: #6
CREATE TABLE mcvt (a int, b int);
INSERT INTO mcvt SELECT x % 2, x % 2 FROM generate_series(1, 1000) x;
CREATE STATISTICS mcvt_s (mcv) ON a, b FROM mcvt;
ANALYZE mcvt;
SELECT pg_restore_extended_stats('schemaname', 'public', 'relname', 'mcvt', 'statistics_schemaname', 'public', 'statistics_name', 'mcvt_s', 'inherited', false, 'most_common_vals', '{{0,0},{1,1}}'::text[], 'most_common_freqs', '{NaN,0.3}'::double precision[], 'most_common_base_freqs', '{0.1,0.1}'::double precision[]);
SELECT * FROM mcvt WHERE a = 0 AND b = 0;
