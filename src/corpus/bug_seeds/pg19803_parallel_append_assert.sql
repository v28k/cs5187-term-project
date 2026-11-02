-- BUG #19803: assertion failure with a parallel Append over an inheritance
-- parent and a materialized CTE. Found by the LLM-fragment arm through a TLP
-- check. Confirmed upstream and fixed on master (abda2a2c, after 28 Oct 2026);
-- reproduces on builds before the fix, e.g. the base build 26bd08fb.
CREATE TABLE pi (a int);
CREATE TABLE pi_child () INHERITS (pi);
WITH c1 AS (SELECT 1 FROM pi WHERE true UNION ALL SELECT 1 FROM pi WHERE false),
     c2 AS MATERIALIZED (SELECT 1)
SELECT 1 FROM c1 UNION ALL SELECT 2 FROM c2;
