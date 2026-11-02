-- pgfuzz failure 81f21381e461 (hang, signature strength: message)
-- test case 1604 from grammar
-- SQLSTATE -: statement ignored statement_timeout and cancel for 10 s; server restarted
-- failing statement: #1
SELECT first_value(x) IGNORE NULLS OVER w FROM (VALUES (1)) v(x)
WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP);
