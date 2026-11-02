-- pgfuzz failure 8a4e039bb76f (assertion, signature strength: stack)
-- test case 802 from grammar
-- SQLSTATE -: consuming input failed: server closed the connection unexpectedly
-- failing statement: #3
CREATE TABLE pi (a int);
CREATE TABLE pi_child () INHERITS (pi);
WITH c1 AS (SELECT 1 FROM pi WHERE true UNION ALL SELECT 1 FROM pi WHERE false),
     c2 AS MATERIALIZED (SELECT 1)
SELECT 1 FROM c1 UNION ALL SELECT 2 FROM c2;
