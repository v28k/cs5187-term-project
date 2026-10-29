-- pgfuzz triage of cde9712bc8db: assertion via assertion
WITH rc(c0) AS (SELECT 1) SELECT FROM (t1 CROSS JOIN JSON_TABLE (CASE WHEN TRUE THEN CASE WHEN (ROW (11, '{"k": 1}') <= ROW (41, '0'::text)) THEN '{"k": 2, "a": [0]}'::jsonb END END, '$[*]' COLUMNS ( c1 text PATH '$')) AS a2);
