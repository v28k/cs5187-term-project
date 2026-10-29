-- pgfuzz triage of ec8b42ef87ac: assertion via assertion
SELECT 100 FROM JSON_TABLE (JSONB_BUILD_ARRAY (100::bigint - CASE WHEN (CASE WHEN COALESCE (ROW ('2000-01-01'::date, 'NaN'::text) <= ROW ('2024-12-31'::date, '35'::text)) THEN 1::bigint END = 1) THEN NULL::bigint END), '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
