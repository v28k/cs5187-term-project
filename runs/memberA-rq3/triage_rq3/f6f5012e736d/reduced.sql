-- pgfuzz triage of f6f5012e736d: assertion via assertion
SELECT '{}'::int[] FROM JSON_TABLE ( ( JSONB_BUILD_ARRAY ( (CASE WHEN FALSE THEN FALSE ELSE ( ('{"k": -1, "a": [1, 2, 3]}'::jsonb, NULL::int) <= ROW ('{"k": 0, "a": [3, 4, 5]}'::jsonb, 16)) END AND TRUE))) - 'k', '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
