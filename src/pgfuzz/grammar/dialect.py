"""Dialect transforms applied to rendered SQL (after generation, before execution).

The grammar and the literal tables are written in PostgreSQL syntax. Some engines do not
accept a few pervasive PostgreSQL spellings; instead of duplicating grammar rules, a
dialect data file (``dialect_data:`` of the grammar generator) can ask for token-level
rewrites that every generated statement and every metamorphic check goes through:

``cast_style: function``
    ``x::T`` becomes ``CAST(x AS T')`` where ``T'`` comes from ``cast_types`` (PostgreSQL
    type spelling -> engine type). The operand is the primary expression left of ``::``:
    a parenthesised expression, a function call, ``CASE ... END``, a literal, ``NULL`` or a
    (qualified) column name.
``functions``
    rename functions, e.g. ``{GREATEST: MAX, LEAST: MIN}`` (only where followed by ``(``).

The rewrite is purely syntactic and keeps the derivation tree untouched, so the oracles
(which compare results) are unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pgfuzz.triage.sqltok import Tok, lex, matching, render

# words after which "(" does not start a function call
_NOT_FUNC = {"AND", "OR", "NOT", "IN", "WHEN", "THEN", "ELSE", "SELECT", "WHERE", "FROM", "ON", "AS", "BY", "EXISTS",
             "ANY", "ALL", "SOME", "VALUES", "RETURNING", "SET", "USING", "IS", "LIKE", "ILIKE", "BETWEEN", "HAVING",
             "CASE", "OVER", "FILTER", "WITHIN", "INTO", "JOIN", "LATERAL", "TABLE", "UNION", "INTERSECT",
             "EXCEPT", "ARRAY", "ROW", "DISTINCT", "WITH", "RECURSIVE", "ORDER", "GROUP", "PARTITION", "AND"}


@dataclass
class Dialect:
    cast_style: str = "operator"                       # "operator" (x::T) or "function" (CAST(x AS T))
    cast_types: dict[str, str] = field(default_factory=dict)
    functions: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_data(cls, data: dict[str, Any] | None) -> "Dialect":
        data = data or {}
        return cls(str(data.get("cast_style", "operator")),
                   {str(k).lower(): str(v) for k, v in (data.get("cast_types") or {}).items()},
                   {str(k).upper(): str(v) for k, v in (data.get("functions") or {}).items()})

    @property
    def active(self) -> bool:
        return self.cast_style == "function" or bool(self.functions)

    def apply(self, sql: str) -> str:
        if not self.active or not sql:
            return sql
        toks = lex(sql)
        if self.functions:
            toks = self._rename(toks)
        if self.cast_style == "function":
            for _ in range(500):                 # one cast per pass; nested casts need several
                new = self._one_cast(toks)
                if new is None:
                    break
                toks = new
        return render(toks)

    # ------------------------------------------------------------------ helpers
    def _rename(self, toks: list[Tok]) -> list[Tok]:
        out = list(toks)
        for i, t in enumerate(out):
            if t.kind == "word" and t.upper in self.functions and i + 1 < len(out) and out[i + 1].text == "(":
                out[i] = Tok(self.functions[t.upper], "word", t.space)
        return out

    def _type_span(self, toks: list[Tok], i: int) -> int:
        """End (exclusive) of the type name starting at token i (``int``, ``int[]``, ``numeric(10, 2)``,
        ``double precision``)."""
        j = i + 1
        if j < len(toks) and toks[i].upper == "DOUBLE" and toks[j].upper == "PRECISION":
            j += 1
        if j < len(toks) and toks[j].text == "(":
            m = matching(toks)
            j = m.get(j, j) + 1
        while j + 1 < len(toks) and toks[j].text == "[" and toks[j + 1].text == "]":
            j += 2
        return j

    def _operand_start(self, toks: list[Tok], k: int) -> int | None:
        """Start index of the primary expression that ends at token k (inclusive)."""
        t = toks[k]
        if t.text in (")", "]"):
            m = matching(toks)
            opens = [o for o, c in m.items() if c == k]
            if not opens:
                return None
            o = opens[0]
            # function call / array constructor: name before "("
            if o > 0 and toks[o - 1].kind == "word" and toks[o - 1].upper not in _NOT_FUNC - {"ARRAY", "ROW"}:
                o -= 1
            elif o > 0 and toks[o - 1].kind == "word" and toks[o - 1].upper in ("ARRAY", "ROW"):
                o -= 1
            return o
        if t.kind == "word" and t.upper == "END":
            depth = 0
            for j in range(k, -1, -1):
                u = toks[j].upper if toks[j].kind == "word" else ""
                if u == "END":
                    depth += 1
                elif u == "CASE":
                    depth -= 1
                    if depth == 0:
                        return j
            return None
        if t.kind in ("str", "num", "ident", "word"):
            j = k
            while j >= 2 and toks[j - 1].text == "." and toks[j - 2].kind in ("word", "ident"):
                j -= 2
            return j
        return None

    def _one_cast(self, toks: list[Tok]) -> list[Tok] | None:
        # innermost first: the last "::" whose operand contains no other "::"
        for i in range(len(toks) - 1, -1, -1):
            if toks[i].kind != "cast" or i == 0 or i + 1 >= len(toks):
                continue
            start = self._operand_start(toks, i - 1)
            if start is None:
                continue
            tend = self._type_span(toks, i + 1)
            tname = render(toks[i + 1:tend])
            target = self.cast_types.get(tname.lower(), self.cast_types.get(tname.lower().split("(")[0], tname))
            operand = toks[start:i]
            operand = [Tok(operand[0].text, operand[0].kind, False)] + operand[1:]
            new = ([Tok("CAST", "word", toks[start].space), Tok("(", "punct", False)] + operand
                   + [Tok("AS", "word", True)] + lex(target) + [Tok(")", "punct", False)])
            return toks[:start] + new + toks[tend:]
        return None
