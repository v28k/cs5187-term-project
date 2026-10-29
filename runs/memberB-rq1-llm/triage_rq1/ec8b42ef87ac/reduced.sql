-- pgfuzz triage of ec8b42ef87ac: assertion via assertion
SELECT FROM JSON_TABLE (JSON_QUERY (JSONB_INSERT ( ( JSONB_BUILD_ARRAY ( (7, ARRAY[1]) >= ROW (16, '{1,2,3,4}'::int[]))), '{a,0}', '{"k": 1, "a": [1, 2]}'::jsonb), '$.a[1]'), '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
