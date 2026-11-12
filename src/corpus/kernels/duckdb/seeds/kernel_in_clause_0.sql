-- rule kernel: in_clause (duckdb)
SELECT TRUE AS c0, 1.5::numeric AS c1 UNION (SELECT TRUE AS c0, 0.0::numeric AS c1 UNION BY NAME SELECT LIST_CONTAINS ([NULL, 1]::int[], a1.c0) AS c0, 2.25::numeric AS c1 FROM t3 AS a1);
