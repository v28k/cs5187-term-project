CREATE TABLE rb_ja (id int PRIMARY KEY, b_id int);
CREATE TABLE rb_jb (id int PRIMARY KEY, c_id int);
INSERT INTO rb_ja VALUES (0, 0), (1, NULL);
INSERT INTO rb_jb VALUES (0, 0), (1, NULL);
SELECT j.b_id, (SELECT j.b_id) FROM (rb_ja LEFT JOIN rb_jb ON rb_ja.b_id = rb_jb.id) j;
