-- pgfuzz triage of cde9712bc8db: assertion via assertion
SELECT FROM t4, JSON_TABLE (JSONB_BUILD_ARRAY (CASE '{"k": 2, "a": [0]}'::jsonb WHEN '{"k": 0, "a": [3, 4, 5]}'::jsonb THEN FALSE WHEN '{"k": 2, "a": [0]}'::jsonb THEN ( ('2024-01-01'::date, 3) >= ROW ('2024-01-01'::date, 21)) ELSE FALSE END), '$[*]' COLUMNS ( c1 text PATH '$')) AS a2;
