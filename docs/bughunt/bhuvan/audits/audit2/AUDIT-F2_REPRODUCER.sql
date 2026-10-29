-- AUDIT-F2 reproducer
-- first_value() / nth_value() with IGNORE NULLS never return when the window
-- has no ORDER BY, the frame ends at UNBOUNDED FOLLOWING, and the frame uses
-- EXCLUDE GROUP or EXCLUDE TIES.
--
-- Affected: PostgreSQL 19 (REL_19_STABLE) and master (20devel).
-- Not affected: 18 and earlier (IGNORE NULLS does not exist there).
--
-- WARNING: on an affected server the last statement below never finishes,
-- and the backend ignores statement_timeout, pg_cancel_backend(),
-- pg_terminate_backend() and "pg_ctl stop -m fast".  Run it only on a
-- disposable cluster.  The only way to stop the backend is SIGKILL, after
-- which the postmaster restarts every session (crash recovery).
--
-- No tables, extensions or special settings are needed.  Run with
--   psql -X -f AUDIT-F2_REPRODUCER.sql

\pset null '(null)'

-- Control 1: the same window without IGNORE NULLS.  Returns at once.
-- With no ORDER BY every row is a peer of the current row, so EXCLUDE GROUP
-- removes all of them and the frame is empty.
SELECT first_value(x) OVER w
FROM (VALUES (1)) v(x)
WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP);
-- expected and actual:  first_value = (null), 1 row

-- Control 2: the same frame computed through the aggregate path.  Returns at once.
SELECT (array_agg(x) FILTER (WHERE x IS NOT NULL) OVER w)[1] AS first_nonnull
FROM (VALUES (1)) v(x)
WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP);
-- expected and actual:  first_nonnull = (null), 1 row

-- The bug.  A statement_timeout is set to show that it does not help.
SET statement_timeout = '5s';
SELECT first_value(x) IGNORE NULLS OVER w
FROM (VALUES (1)) v(x)
WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP);
-- expected:  first_value = (null), 1 row, at once (the frame is empty)
-- actual:    never returns; the backend uses 100% of one CPU and is not
--            stopped by the 5 s statement_timeout, pg_cancel_backend() or
--            pg_terminate_backend()

-- Other shapes that hang the same way (run each in its own session):
--
-- EXCLUDE TIES, current row NULL (expected: x=(null) -> (null), x=2 -> 2):
--   SELECT x, first_value(x) IGNORE NULLS OVER (ROWS BETWEEN UNBOUNDED PRECEDING
--          AND UNBOUNDED FOLLOWING EXCLUDE TIES)
--   FROM (VALUES (NULL::int), (2)) v(x);
--
-- nth_value, frame with one non-null value (expected: (null) for both rows):
--   SELECT nth_value(x, 2) IGNORE NULLS OVER (ROWS BETWEEN CURRENT ROW
--          AND UNBOUNDED FOLLOWING EXCLUDE TIES)
--   FROM (VALUES (1), (2)) v(x);
--
-- RANGE mode, and PARTITION BY without ORDER BY (expected: (null)):
--   SELECT first_value(x) IGNORE NULLS OVER (RANGE BETWEEN UNBOUNDED PRECEDING
--          AND UNBOUNDED FOLLOWING EXCLUDE GROUP) FROM (VALUES (1)) v(x);
--   SELECT first_value(x) IGNORE NULLS OVER (PARTITION BY x ROWS BETWEEN
--          UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP)
--   FROM (VALUES (1), (2)) v(x);
