-- B-01: FULL JOIN that works on 18.x fails on 19/master after NOT-NULL-based
-- constant folding removes the only hash/merge-joinable join clause.
DROP TABLE IF EXISTS fa, fb;
CREATE TABLE fa (id int PRIMARY KEY, x int NOT NULL, flag bool NOT NULL);
CREATE TABLE fb (id int, y int, flag bool);
INSERT INTO fa VALUES (1, 0, true), (2, 1, false);
INSERT INTO fb VALUES (1, 0, true), (2, NULL, false), (3, NULL, NULL);

-- 1. NullTest on a NOT NULL column (fa.x IS NULL is folded to false)
SELECT fa.id, fb.id FROM fa FULL JOIN fb ON (fa.x IS NULL) = (fb.y IS NULL) ORDER BY 1, 2;
-- 2. same, through a cast
SELECT fa.id, fb.id FROM fa FULL JOIN fb ON fb.y = (fa.x IS NULL)::int ORDER BY 1, 2;
-- 3. primary key column, IS NOT NULL
SELECT fa.id, fb.id FROM fa FULL JOIN fb ON fb.flag = (fa.id IS NOT NULL) ORDER BY 1, 2;
-- 4. BooleanTest on a NOT NULL boolean (IS UNKNOWN is folded to false)
SELECT fa.id, fb.id FROM fa FULL JOIN fb ON fb.flag = (fa.flag IS UNKNOWN) ORDER BY 1, 2;
-- 5. row-wise IS NULL with NOT NULL fields
SELECT fa.id, fb.id FROM fa FULL JOIN fb ON fb.flag = (ROW(fa.x, fa.id) IS NULL) ORDER BY 1, 2;
-- control: the same join with LEFT JOIN works on both (nestloop is allowed)
SELECT fa.id, fb.id FROM fa LEFT JOIN fb ON (fa.x IS NULL) = (fb.y IS NULL) ORDER BY 1, 2;
