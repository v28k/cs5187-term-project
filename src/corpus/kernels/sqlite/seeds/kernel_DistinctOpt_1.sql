-- rule kernel: DistinctOpt (sqlite)
CREATE TABLE t (a,b,c,d);
INSERT INTO t VALUES (1,2,3,4),(2,3,4,5);
SELECT DISTINCT c FROM t;
