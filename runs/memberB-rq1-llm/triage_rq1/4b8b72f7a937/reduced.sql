-- pgfuzz triage of 4b8b72f7a937: assertion via assertion
SELECT FROM (t0 JOIN JSON_TABLE (JSON_ARRAY (ROW (33, 100.0) <= ROW (16, 42.5::numeric)), '$[*]' COLUMNS (c0 int PATH '$.k')) AS a2 ON TRUE);
