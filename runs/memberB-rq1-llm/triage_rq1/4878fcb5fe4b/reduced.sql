-- pgfuzz triage of 4878fcb5fe4b: assertion via assertion
SELECT FROM JSON_TABLE (CASE WHEN ( (1.0::float8, '_'::text) > ROW ('50', 'A') AND NULL) THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb END, '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
