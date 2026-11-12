-- rule kernel: GroupByOrder (sqlite)
CREATE INDEX t_g ON t(g);
CREATE TABLE t(v TEXT, k INTEGER);
INSERT INTO t VALUES ('a',3),('b',2),('a',1),('c',4),('b',5);
CREATE TABLE t(v TEXT, k TEXT);
INSERT INTO t VALUES ('one','b'),('two',NULL),('three','A'),('four','a');
CREATE TABLE t(v TEXT, sep TEXT, k INTEGER);
INSERT INTO t VALUES ('b','/',2),('c',';',3),('a',':',1);
CREATE TABLE t(v INTEGER, k INTEGER);
INSERT INTO t VALUES (2,2),(1,1);
INSERT INTO t VALUES (1,'b',4),(2,'y',4);
PRAGMA temp_store=FILE;
PRAGMA cache_size=1;
CREATE TABLE t(g INTEGER, v INTEGER);
SELECT NULL FROM t GROUP BY g ORDER BY g;
