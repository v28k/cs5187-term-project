**Title:** panic (unreachable!) in window planning: window function over DATE()/DATETIME() referenced twice in ORDER BY

```sql
CREATE TABLE tl (c0 INTEGER, c1 TEXT);
INSERT INTO tl VALUES (1, 'a'), (2, 'b');
SELECT c0, LAG(DATE()) OVER () FROM tl ORDER BY 2, 2;
```

panics:

```
panicked at core/translate/window.rs:3428:22:
internal error: entered unreachable code: lag/lead arg[0] must be a buffer column reference after planner rewrite,
got Some(FunctionCall { name: Name { quote: None, value: "DATE" }, args: [], ... })
```

The same with `FIRST_VALUE(DATETIME())` (window.rs:3564, "first_value/nth_value arg[0] must be a subquery column ref
after planner rewrite") and with an alias (`... OVER () AS w ... ORDER BY w, w`). All of these work: `ORDER BY 2` (once),
no ORDER BY, `LAG(c1)`, `LAG(upper(c1))`, `LAG(1)`. SQLite 3.54.1 runs all of them.

Version: pyturso 0.8.3 (Linux x86_64). Found with a grammar-based SQL fuzzer.
