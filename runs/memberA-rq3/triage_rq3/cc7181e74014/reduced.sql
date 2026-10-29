-- pgfuzz triage of cc7181e74014: assertion via assertion
SELECT FROM (JSON_TABLE (CASE WHEN ( (500, 10::bigint) <= (10, 1::bigint)) THEN '{"k": 0, "a": [3, 4, 5]}'::jsonb ELSE '{"k": 0, "a": [3, 4, 5]}'::jsonb END, '$[*]' COLUMNS (c0 int PATH '$.k')) AS a1 JOIN tp AS a2 ON TRUE);
