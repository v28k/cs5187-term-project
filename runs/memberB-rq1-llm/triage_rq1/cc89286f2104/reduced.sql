-- pgfuzz triage of cc89286f2104: assertion via assertion
SELECT FROM JSON_TABLE ( ( CASE WHEN ( (100.0, '0'::interval) >= (NULL::numeric, '00:00:00.000001'::interval)) THEN '{"k": -1, "a": [1, 2, 3]}' END), '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
