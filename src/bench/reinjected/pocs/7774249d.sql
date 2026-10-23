WITH data(x) AS (VALUES ('Inf'::float8),(2::float8),(3::float8)) SELECT covar_pop(x, 0::float8) FROM data;
WITH data(x) AS (VALUES (1::float8),('NaN'::float8),(3::float8)) SELECT covar_pop(x, 0::float8) FROM data;
WITH data(x) AS (VALUES (0::float8),(0::float8),(0::float8)) SELECT regr_slope(x, 'Inf'::float8), corr(x, 'NaN') FROM data;
