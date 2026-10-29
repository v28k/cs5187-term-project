-- pgfuzz triage of f6f5012e736d: assertion via assertion
SELECT ARRAY[1] FROM JSON_TABLE ( ( JSONB_BUILD_ARRAY ( (CASE WHEN FALSE THEN FALSE ELSE (ROW ('{"k": -1, "a": [1, 2, 3]}'::jsonb, NULL::int) <= ROW ('{"k": 0, "a": [3, 4, 5]}', 16)) END AND TRUE))) - 'k', '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
