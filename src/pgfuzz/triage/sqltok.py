"""A small SQL lexer and parenthesis tree for test-case reduction.

The reducer does not need a full SQL parser. It needs to know where tokens end
(so it never cuts a string literal or an operator in half), how parentheses and
brackets nest (so it can remove or replace a whole sub-expression, the
hierarchy that Hierarchical Delta Debugging works on), and where clause
keywords and list separators are at each nesting level.

Rendering keeps the original spacing of every kept token and inserts a space
where deleting tokens would glue two words or two operators together.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<comment>--[^\n]*)
  | (?P<str>[EeBbXxUu]&?'(?:[^'\\]|\\.|'')*'|'(?:[^']|'')*')
  | (?P<dollar>\$(?P<tag>[A-Za-z_]*)\$.*?\$(?P=tag)\$)
  | (?P<ident>"(?:[^"]|"")*")
  | (?P<num>\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)
  | (?P<word>[A-Za-z_][A-Za-z0-9_$]*)
  | (?P<cast>::)
  | (?P<punct>[(),;\[\].])
  | (?P<op>[+\-*/<>=~!@#%^&|`?]+)
  | (?P<other>.)
    """,
    re.X | re.S,
)


@dataclass(frozen=True)
class Tok:
    text: str
    kind: str          # word | num | str | ident | op | cast | punct | other | hole
    space: bool = True  # whitespace before this token in the source

    @property
    def upper(self) -> str:
        return self.text.upper() if self.kind == "word" else self.text


HOLE = Tok("\x00HOLE\x00", "hole")


def lex(sql: str) -> list[Tok]:
    out: list[Tok] = []
    space = False
    for m in _TOKEN.finditer(sql):
        kind = m.lastgroup or "other"
        if kind in ("ws", "comment"):
            space = True
            continue
        if kind == "tag":
            kind = "dollar"
        out.append(Tok(m.group(), kind, space))
        space = False
    return out


def _wordish(t: Tok) -> bool:
    return t.kind in ("word", "num", "str", "ident", "dollar", "hole")


def render(toks: list[Tok]) -> str:
    parts: list[str] = []
    prev: Tok | None = None
    for t in toks:
        if prev is not None:
            glue = (_wordish(prev) and _wordish(t)) or (prev.kind == "op" and t.kind == "op")
            if t.space or glue:
                parts.append(" ")
        parts.append(t.text)
        prev = t
    return "".join(parts)


# ------------------------------------------------------------------ structure

_OPEN = {"(": ")", "[": "]"}

# Keywords that start a clause; a clause runs to the next keyword of this set at
# the same nesting level (or to the end of the level).
CLAUSE_KEYWORDS = ("WHERE", "GROUP", "HAVING", "ORDER", "LIMIT", "OFFSET", "WINDOW", "RETURNING",
                   "ON", "USING", "FILTER", "WITH", "UNION", "INTERSECT", "EXCEPT")


def matching(toks: list[Tok]) -> dict[int, int]:
    """Index of every opening parenthesis/bracket -> index of its closing one."""
    out: dict[int, int] = {}
    stack: list[tuple[str, int]] = []
    for i, t in enumerate(toks):
        if t.kind == "punct" and t.text in _OPEN:
            stack.append((t.text, i))
        elif t.kind == "punct" and t.text in (")", "]") and stack:
            o, j = stack.pop()
            if _OPEN[o] == t.text:
                out[j] = i
    return out


def levels(toks: list[Tok]) -> list[tuple[int, int]]:
    """Every nesting level as a ``(start, end)`` token range (exclusive), outermost first:
    the whole statement, then the inside of every parenthesis pair."""
    m = matching(toks)
    spans = [(0, len(toks))] + sorted(((o + 1, c) for o, c in m.items()), key=lambda s: -(s[1] - s[0]))
    return spans


def depth_zero(toks: list[Tok], start: int, end: int) -> list[int]:
    """Indices in ``[start, end)`` that are not inside a nested parenthesis pair."""
    out = []
    depth = 0
    for i in range(start, end):
        t = toks[i]
        if t.kind == "punct" and t.text in _OPEN:
            if depth == 0:
                out.append(i)
            depth += 1
        elif t.kind == "punct" and t.text in (")", "]"):
            depth -= 1
            if depth == 0:
                out.append(i)
        elif depth == 0:
            out.append(i)
    return out


# Keywords after which a comma-separated list starts (select list, FROM list, ...).
REGION_HEADS = frozenset(CLAUSE_KEYWORDS) | {"SELECT", "FROM", "SET", "VALUES", "BY", "DISTINCT", "ALL"}


def list_regions(toks: list[Tok], start: int, end: int) -> list[tuple[int, int]]:
    """Ranges of one level between clause heads (``SELECT``, ``FROM``, ``BY``, ...)."""
    top = depth_zero(toks, start, end)
    heads = [i for i in top if toks[i].kind == "word" and toks[i].upper in REGION_HEADS]
    bounds = [start - 1] + heads + [end]
    return [(bounds[k] + 1, bounds[k + 1]) for k in range(len(bounds) - 1) if bounds[k + 1] > bounds[k] + 1]


def list_items(toks: list[Tok], start: int, end: int) -> list[tuple[int, int]]:
    """Comma-separated items of one region, as token ranges without the commas."""
    top = depth_zero(toks, start, end)
    commas = [i for i in top if toks[i].kind == "punct" and toks[i].text == ","]
    if not commas:
        return []
    bounds = [start - 1] + commas + [end]
    return [(bounds[k] + 1, bounds[k + 1]) for k in range(len(bounds) - 1)]


def delete_items(toks: list[Tok], items: list[tuple[int, int]], i: int, j: int) -> list[Tok]:
    """Remove items ``i..j`` (inclusive) of a list together with the right commas."""
    if j < len(items) - 1:
        a, b = items[i][0], items[j + 1][0]          # up to the next item (takes the comma after j)
    elif i > 0:
        a, b = items[i - 1][1], items[j][1]          # from the comma before i
    else:
        a, b = items[0][0], items[-1][1]
    return toks[:a] + toks[b:]


def clauses(toks: list[Tok], start: int, end: int) -> list[tuple[int, int]]:
    """Clause ranges of one level: from a clause keyword to the next one."""
    top = depth_zero(toks, start, end)
    heads = [i for i in top if toks[i].kind == "word" and toks[i].upper in CLAUSE_KEYWORDS]
    out = []
    for k, h in enumerate(heads):
        nxt = heads[k + 1] if k + 1 < len(heads) else end
        if toks[h].upper == "WITH" and k == 0 and h == start:
            continue   # a leading WITH is needed by the rest of the statement
        out.append((h, nxt))
    return out
