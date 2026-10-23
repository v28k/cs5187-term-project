-- a non-NULL IS DISTINCT FROM over an equality operator that returns NULL (record = record with NULL fields)
CREATE TABLE rb_tr (id int, a int, b int);
INSERT INTO rb_tr VALUES (1, 1, NULL), (2, NULL, NULL), (3, 1, 2);
SELECT id FROM rb_tr WHERE NOT ((ROW(a, 1) IS DISTINCT FROM ROW(1, 1)) IS NOT NULL) ORDER BY id;
SELECT id, (ROW(a, b) IS DISTINCT FROM ROW(1, b)) IS NULL FROM rb_tr ORDER BY id;
