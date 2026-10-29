-- pgfuzz triage of 381a793a6668: assertion via assertion
SELECT FROM JSON_TABLE ( ( CASE WHEN ( (100.0, '0'::interval) >= (NULL::numeric, '00:00:00.000001'::interval)) THEN '{}' END), '$[*]' COLUMNS ( c1 text PATH '$')) AS a1;
