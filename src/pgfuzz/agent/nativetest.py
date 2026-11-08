"""Regression tests in each engine's own test format (D3).

DuckDB ``.test`` and DataFusion / SQLite ``.slt`` are sqllogictest dialects; Turso uses its
``.sqltest`` format. A test has setup statements, then either a query with its expected
rows or a statement that must fail / succeed.
"""

from __future__ import annotations

from typing import Any

FORMATS = {"duckdb": ".test", "datafusion": ".slt", "sqlite": ".slt", "turso": ".sqltest", "postgres": ".sql"}


def _col_type(values: list[Any]) -> str:
    for v in values:
        if v is None:
            continue
        s = str(v)
        try:
            int(s)
            return "I"
        except ValueError:
            pass
        try:
            float(s)
            return "R"
        except ValueError:
            return "T"
    return "T"


def _fmt(v: Any) -> str:
    return "NULL" if v is None else str(v)


def native_test(engine: str, name: str, setup: list[str], query: str, rows: list[list[Any]] | None = None,
                error: str | None = None, description: str = "") -> str:
    """Render one regression test. ``rows`` = expected rows of ``query``; ``error`` = the query must
    fail with this message fragment; neither = the query must succeed."""
    setup = [s.strip().rstrip(";") for s in setup if s.strip()]
    query = query.strip().rstrip(";")
    if engine == "turso":
        body = "\n".join(f"    {s};" for s in setup + [query])
        if error is not None:
            exp = f"expect error {{\n    {error}\n}}"
        else:
            exp = "expect {\n" + "\n".join("    " + "|".join(_fmt(v) for v in r) for r in rows or []) + "\n}"
        return f"@database :memory:\n\n# {description}\ntest {name} {{\n{body}\n}}\n{exp}\n"
    out: list[str] = []
    if engine == "duckdb":
        out += [f"# name: test/sql/fuzzer/{name}.test", f"# description: {description}", "# group: [fuzzer]", ""]
    else:
        out += [f"# {description}", ""]
    for s in setup:
        out += ["statement ok", s + ";", ""]
    if error is not None:
        out += ["statement error", query + ";", "----", error, ""]
    elif rows is None:
        out += ["statement ok", query + ";", ""]
    else:
        ncols = max((len(r) for r in rows), default=1)
        types = "".join(_col_type([r[i] for r in rows if i < len(r)]) for i in range(ncols))
        sep = "\t" if engine == "duckdb" else " "
        out += [f"query {types} rowsort", query + ";", "----"]
        out += [sep.join(_fmt(v) for v in r) for r in rows]
        out.append("")
    return "\n".join(out)
