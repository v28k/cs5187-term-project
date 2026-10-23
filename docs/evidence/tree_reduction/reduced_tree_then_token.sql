-- pgfuzz triage of tc1: assertion via assertion
SELECT CASE CASE WHEN FALSE THEN '{a,b}'::text[] ELSE (SELECT MAX ('{NULL}'::text[]) FROM JSON_TABLE (CASE WHEN (ROW (10.0::numeric, 10) >= ROW (0.0, 1) IS FALSE) THEN '{"k": -1, "a": [1, 2, 3]}'::jsonb END, '$.a[*]' COLUMNS ( c1 int PATH '$')) AS a3) END WHEN '{a,b,c,d}'::text[] THEN '{NULL,1}'::int[] END a1;
