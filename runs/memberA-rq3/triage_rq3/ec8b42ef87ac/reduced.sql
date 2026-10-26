-- pgfuzz triage of ec8b42ef87ac: assertion via assertion
SELECT 1 FROM JSON_TABLE (JSONB_BUILD_ARRAY (100 - CASE WHEN (CASE WHEN COALESCE (ROW ('2024-12-31'::date, 'NaN'::text) <= ROW ('2024-01-01', '35'::text)) THEN 1::bigint END = 1) THEN 1::bigint END), '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
