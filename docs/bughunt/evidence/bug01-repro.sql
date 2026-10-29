\echo === Q1 row compare in context item (expect t)
SELECT * FROM JSON_TABLE(jsonb_build_object('k', ROW(1, 2) < ROW(3, 4)), '$' COLUMNS (a bool PATH '$.k'));
\echo === Q2 text compare COLLATE C in context item (expect t)
SELECT * FROM JSON_TABLE(jsonb_build_object('k', 'a' < 'b' COLLATE "C"), '$' COLUMNS (a bool PATH '$.k'));
\echo === Q3 text compare in PASSING (expect t)
SELECT * FROM JSON_TABLE(jsonb '{}', '$' PASSING 'a' < 'b' COLLATE "C" AS x COLUMNS (a bool PATH '$x'));
\echo === Q4 row compare in PASSING (expect t)
SELECT * FROM JSON_TABLE(jsonb '{}', '$' PASSING ROW(1, 2) < ROW(3, 4) AS x COLUMNS (a bool PATH '$x'));
\echo === Controls: same expressions outside JSON_TABLE
SELECT ROW(1, 2) < ROW(3, 4) AS plain_row, 'a' < 'b' COLLATE "C" AS plain_text;
SELECT JSON_QUERY(jsonb_build_object('k', ROW(1, 2) < ROW(3, 4)), '$.k') AS json_query_row;
-- \echo === Control: XMLTABLE equivalent
-- (needs a --with-libxml build) SELECT * FROM XMLTABLE('/r' PASSING xmlelement(name r, ROW(1,2) < ROW(3,4)) COLUMNS a text PATH '.');
