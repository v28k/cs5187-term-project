"""A data profile of the fuzzing schema, for literals that hit the data.

Random constants rarely matter: ``c0 = 4711`` selects nothing and ``c0 < 4711``
selects everything, so the executor code behind a selective predicate (index
ranges, partial matches, partition pruning at a boundary) is never reached.
The profile records, for every column of the schema, the values the data
actually has; the engine then draws some literals from it:

* **quantile literals** (constraint-based selection): the 10 % ... 90 % quantiles
  of the values of that type, so ``col < q`` or ``col = q`` selects a real share
  of the rows;
* **boundary literals** (interval analysis): min, max, min - 1 and max + 1 of the
  observed interval, plus the edges of the type itself (0, -0, NaN, +-Infinity,
  the largest int, the empty array, the empty string).

    python -m pgfuzz profile configs/local.yaml --out corpus/profile.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pgfuzz.grammar.schema import Schema

ORDERED = {"int", "bigint", "numeric", "float8", "text", "date", "tstz", "interval"}
NUMERIC = {"int", "bigint", "numeric", "float8"}
TYPE_EDGES = {
    "int": ["0", "(-1)", "2147483647", "(-2147483648)"],
    "bigint": ["0::bigint", "9223372036854775807::bigint", "(-9223372036854775808)::bigint"],
    "numeric": ["0::numeric", "'NaN'::numeric", "'-0.0'::numeric", "0.000000001::numeric"],
    "float8": ["'NaN'::float8", "'Infinity'::float8", "'-Infinity'::float8", "'-0'::float8", "5e-324::float8"],
    "text": ["''::text", "' '::text", "'%'::text", "'\\\\'::text"],
    "date": ["'infinity'::date", "'-infinity'::date", "'2000-02-29'::date"],
    "tstz": ["'infinity'::timestamptz", "'-infinity'::timestamptz"],
    "interval": ["'0'::interval", "'-1 day'::interval"],
    "intarr": ["'{}'::int[]", "'{NULL}'::int[]"],
    "textarr": ["'{}'::text[]", "'{\"\"}'::text[]"],
}


def collect(executor: Any, schema: Schema, sql_type: dict[str, str]) -> dict[str, Any]:
    """Query the server (after the executor's setup) for every orderable column."""
    base = getattr(executor, "test", executor)
    if not base._alive():
        base._connect(wait=True)
    conn = base.conn
    cols: dict[str, Any] = {}
    for rel in schema.relations.values():
        for c in rel.columns:
            if c.type not in ORDERED:
                continue
            pct = ", ".join(f"(percentile_disc({p}) WITHIN GROUP (ORDER BY {c.name}))::text"
                            for p in (0.1, 0.25, 0.5, 0.75, 0.9))
            q = f"SELECT min({c.name})::text, max({c.name})::text, count(*), count({c.name}), {pct} FROM {rel.name}"
            try:
                mn, mx, n, nn, *qs = conn.execute(q).fetchone()
            except Exception as e:  # a view or type the profile cannot order
                cols[f"{rel.name}.{c.name}"] = {"type": c.type, "error": str(e).splitlines()[0][:120]}
                continue
            cols[f"{rel.name}.{c.name}"] = {"type": c.type, "sql_type": sql_type.get(c.type, c.type), "min": mn,
                                            "max": mx, "rows": int(n), "non_null": int(nn),
                                            "quantiles": [x for x in dict.fromkeys(qs) if x is not None]}
    return {"columns": cols}


def _lit(v: str, sqlt: str) -> str:
    return "'" + str(v).replace("'", "''") + "'::" + sqlt


def _neighbours(v: str, t: str) -> list[str]:
    if t in ("int", "bigint"):
        try:
            return [str(int(v) - 1), str(int(v) + 1)]
        except ValueError:
            return []
    if t in ("numeric", "float8"):
        try:
            f = float(v)
            return [repr(f - 1), repr(f + 1)]
        except ValueError:
            return []
    return []


class Profile:
    """Literal pools per grammar type, built from a profile file."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.quantile: dict[str, list[str]] = {}
        self.by_col: dict[tuple[str, str], list[str]] = {}     # (relation, column) -> its quantiles
        self.boundary: dict[str, list[str]] = {t: list(v) for t, v in TYPE_EDGES.items()}
        for key, col in data.get("columns", {}).items():
            if "error" in col or col.get("min") is None:
                continue
            t, st = col["type"], col["sql_type"]
            rel, _, name = key.partition(".")
            self.by_col[(rel, name)] = sorted({_lit(q, st) for q in col.get("quantiles") or [] if q is not None})
            self.quantile.setdefault(t, []).extend(_lit(q, st) for q in col.get("quantiles") or [] if q is not None)
            pool = self.boundary.setdefault(t, [])
            for v in (col["min"], col["max"]):
                pool.append(_lit(v, st))
                pool.extend(_lit(x, st) for x in _neighbours(v, t))
        for d in (self.quantile, self.boundary):
            for t in d:
                d[t] = sorted(set(d[t]))

    @classmethod
    def load(cls, path: str | Path) -> "Profile":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def for_column(self, rel: str, col: str, rng: Any) -> str | None:
        vals = self.by_col.get((rel, col))
        return rng.choice(vals) if vals else None

    def pick(self, t: str, rng: Any) -> str | None:
        q, b = self.quantile.get(t), self.boundary.get(t)
        if q and (not b or rng.random() < 0.6):
            return rng.choice(q)
        return rng.choice(b) if b else None
