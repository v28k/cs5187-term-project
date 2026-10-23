CREATE TABLE rb_nnt (id int NOT NULL, val int NOT NULL);
CREATE TABLE rb_nt (id int, val int);
INSERT INTO rb_nt VALUES (1, NULL);
INSERT INTO rb_nnt VALUES (2, 2);
SELECT * FROM rb_nt t1 WHERE COALESCE(t1.id, -1) NOT IN (SELECT t1.val FROM rb_nnt t2 WHERE t2.val IS NOT NULL);
