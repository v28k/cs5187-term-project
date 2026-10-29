-- pgfuzz triage of cc7181e74014: assertion via assertion
SELECT 'c4ca4238a0b923820dcc509a6f75849b' FROM (JSON_TABLE (TO_JSONB (ROW ('2024-01-01 00:00:00+00', '1 year 2 mons 3 days 04:05:06.789'::interval) <= ROW ('2024-01-06 15:00:00+00'::timestamptz, '70:00:00'::interval)), '$.a[*]' COLUMNS (c0 FOR ORDINALITY)) AS a1 FULL JOIN v0 AS a2 ON NULL);
