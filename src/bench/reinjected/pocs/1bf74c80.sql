CREATE TABLE rb_jb2 (id int PRIMARY KEY, c_id int);
CREATE TABLE rb_jd (a int, b int);
INSERT INTO rb_jb2 VALUES (0, 0), (1, NULL);
INSERT INTO rb_jd VALUES (1,3), (2,2), (3,1);
SELECT d.* FROM rb_jd d LEFT JOIN
  (SELECT DISTINCT ON (id) id, generate_series(1, 2) AS g FROM rb_jb2 ORDER BY id) s
  ON d.a = s.id
  ORDER BY 1, 2;
