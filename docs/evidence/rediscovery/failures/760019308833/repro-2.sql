-- pgfuzz failure 760019308833 (wrong_result, signature strength: diff)
-- test case 673 from grammar
-- SQLSTATE -: metamorphic check tlp_where failed: 1 rows vs 2 rows
-- failing statement: #7
CREATE TABLE f1o (t text NOT NULL);
CREATE TABLE f1s (i int NOT NULL);
INSERT INTO f1o VALUES ('1');
INSERT INTO f1s VALUES (0);
CREATE FUNCTION pgf_i2t(int) RETURNS text IMMUTABLE STRICT LANGUAGE sql AS $$ SELECT CASE WHEN $1 <> 0 THEN $1::varchar END $$;
CREATE CAST (int AS text) WITH FUNCTION pgf_i2t(int) AS IMPLICIT;
SELECT t FROM f1o WHERE t NOT IN (SELECT i FROM f1s);
