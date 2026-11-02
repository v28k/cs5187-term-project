-- BUG #19768: JSON_TABLE does not assign collations to its context item and
-- PASSING arguments. Found by the grammar fuzzer (assertion in execExpr.c).
-- Affected: 17, 18, master (open). On an assertion-enabled build: TRAP.
SELECT * FROM JSON_TABLE(jsonb_build_object('k', ROW(1, 2) < ROW(3, 4)), '$' COLUMNS (a bool PATH '$.k'));
