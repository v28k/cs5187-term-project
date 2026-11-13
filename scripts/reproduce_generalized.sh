#!/usr/bin/env bash
# One-command reproduction of the five bugs the generalized fuzzer found and we filed upstream
# (Turso T-05 and T-08, DuckDB D-01, DataFusion DF-01 and DF-02), on the released versions the
# campaigns ran on. No build and no root needed; about one minute (mostly pip).
#
#   bash scripts/reproduce_generalized.sh      # from the repository root; Python >= 3.10
#
# It creates a virtual environment in .venv-repro with pyturso 0.8.3, duckdb 2.0.0 and
# datafusion 55.0.0, runs the minimal reproducer of each bug (the repro.sql of its package in
# docs/bughunt/) and prints whether the wrong behaviour shows. Expected: 5 of 5. A bug that is
# fixed in a later release no longer reproduces there; the script pins the affected versions.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
VENV=${VENV:-$REPO/.venv-repro}
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --disable-pip-version-check pyturso==0.8.3 duckdb==2.0.0 datafusion==55.0.0
exec "$VENV/bin/python" - <<'PY'
import subprocess, sys

def turso_db(*setup):
    import turso
    cur = turso.connect(":memory:").cursor()
    for s in setup:
        cur.execute(s)
    return cur

def t05():
    cur = turso_db("CREATE TABLE t (a INTEGER, b TEXT)", "INSERT INTO t VALUES (1, 'x'), (2, 'y')")
    got = cur.execute("SELECT percentile_disc(length(b), 1) FROM t").fetchall()
    return got == [(None,)], f"percentile_disc(length(b), 1) = {got[0][0]!r} (SQLite: 1.0)"

def t08():
    cur = turso_db("CREATE TABLE t (x INTEGER)", "INSERT INTO t VALUES (1), (3)")
    try:
        got = cur.execute("SELECT max(x) IN (SELECT 1), count(*) OVER () FROM t").fetchall()
        return False, f"returned {got} (SQLite: 0|1)"
    except Exception as e:
        ok = "misuse of aggregate" in str(e)
    # the extension aggregate panics the process: run it in a child
    child = subprocess.run([sys.executable, "-c",
        "import turso; c = turso.connect(':memory:').cursor(); c.execute('CREATE TABLE t (x INTEGER)');"
        "c.execute('INSERT INTO t VALUES (1), (3)');"
        "c.execute('SELECT median(x) IN (SELECT 2), count(*) OVER () FROM t').fetchall()"],
        capture_output=True, text=True)
    panic = "aggregate called in scalar context" in child.stderr
    return ok, "'misuse of aggregate function max()' (SQLite: 0|1)" + (
        "; median(x) IN (...) with a window panics the process" if panic else "")

def d01():
    import duckdb
    c = duckdb.connect()
    c.execute("CREATE TABLE a (x INTEGER)")
    c.execute("INSERT INTO a VALUES (1), (2)")
    try:
        got = c.execute("SELECT min((SELECT [1])) FROM a").fetchall()
        return False, f"returned {got} (expected [1])"
    except Exception as e:
        return "Cannot copy BoundSubqueryExpression" in str(e), f"{type(e).__name__}: {str(e).splitlines()[0]}"

def df(setup, query):
    from datafusion import SessionContext
    ctx = SessionContext()
    for s in setup:
        ctx.sql(s).collect()
    try:
        got = ctx.sql(query).collect()
        return None, f"returned {got}"
    except Exception as e:
        return str(e), " ".join(str(e).split())[:110]

def df01():
    err, msg = df(["CREATE TABLE t (c0 INT, c1 VARCHAR)", "INSERT INTO t VALUES (1, 'a'), (NULL, 'b')"],
                  "UPDATE t SET c0 = COALESCE(c0, 0)")
    return bool(err and "__common_expr_1" in err), msg

def df02():
    err, msg = df([], "VALUES ((SELECT 1), 5)")
    return bool(err and "ScalarSubqueryExpr evaluated before the subquery was executed" in err), msg

import duckdb, datafusion
from importlib.metadata import version
print(f"pyturso {version('pyturso')}, duckdb {duckdb.__version__}, datafusion {datafusion.__version__}\n")
bugs = [
    ("T-05", "Turso #11594", "percentile_disc/cont of an expression argument", t05),
    ("T-08", "Turso #11796", "aggregate in an IN-subquery operand next to a window function", t08),
    ("D-01", "DuckDB #28551", "min/max of a nested subquery: Cannot copy BoundSubqueryExpression", d01),
    ("DF-01", "DataFusion #27235", "UPDATE with COALESCE: No field named __common_expr_1", df01),
    ("DF-02", "DataFusion DF-02", "VALUES with a scalar subquery: internal error", df02),
]
n = 0
for pid, issue, title, fn in bugs:
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"harness error: {type(e).__name__}: {e}"
    n += ok
    print(f"{'REPRODUCED' if ok else 'not reproduced':15} {pid:6} {issue:18} {title}\n{'':15} {detail}")
print(f"\nGeneralized bugs reproduced: {n} of {len(bugs)}")
sys.exit(0 if n == len(bugs) else 1)
PY
