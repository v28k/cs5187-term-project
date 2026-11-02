-- AUDIT-F2 (pgsql-bugs, 23 Oct 2026; developer replied 24 Oct): first_value()
-- / nth_value() with IGNORE NULLS over a frame that ends at UNBOUNDED FOLLOWING
-- and excludes the current row's peers never returns, and the backend ignores
-- statement_timeout and query cancel. Affected: 19, master. Detected by the hang
-- oracle (the worker's server is restarted to end the backend).
SELECT first_value(x) IGNORE NULLS OVER w FROM (VALUES (1)) v(x)
WINDOW w AS (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING EXCLUDE GROUP);
