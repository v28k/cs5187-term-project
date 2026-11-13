-- rule kernel: P:CombinePartialFinalAggregate (datafusion)
SELECT ' '::text AS c0, 0.0::float8 AS c1, 'abc'::text AS c2 FROM tp AS a1 WHERE (('2000-01-01'::date BETWEEN '1970-01-01'::date AND '1970-01-01'::date) OR (EXTRACT (MICROSECONDS FROM (SELECT MIN ('2000-01-01 00:00:00+00'::timestamptz) FROM t3 AS a2)) IS NULL));
