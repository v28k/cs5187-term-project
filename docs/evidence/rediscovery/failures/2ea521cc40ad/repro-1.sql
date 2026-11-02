-- pgfuzz failure 2ea521cc40ad (assertion, signature strength: stack)
-- test case 794 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #1
VALUES (NORMALIZE(TO_CHAR(CASE WHEN TRUE THEN 'NaN'::numeric ELSE 0.5::numeric END + 0.0::numeric, 'FM999990.00')));
