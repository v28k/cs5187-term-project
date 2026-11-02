-- pgfuzz failure 68e520951660 (assertion, signature strength: stack)
-- test case 294 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #1
SELECT * FROM JSON_TABLE(jsonb_build_object('k', ROW(1, 2) < ROW(3, 4)), '$' COLUMNS (a bool PATH '$.k'));
