"""Split a SQL script into statements without breaking strings, dollar-quoted
bodies, quoted identifiers or comments. ``BEGIN ATOMIC ... END`` bodies are not
special-cased; seed files should use dollar quoting for function bodies."""

from __future__ import annotations

import re

_PIECE = re.compile(
    r"""
    --[^\n]*
  | /\*.*?(?:\*/|\Z)
  | \$(?P<tag>[A-Za-z_][A-Za-z_0-9]*)?\$.*?(?:\$(?(tag)(?P=tag))\$|\Z)
  | [Ee]'(?:[^'\\]|\\.|'')*'?
  | '(?:[^']|'')*'?
  | "(?:[^"]|"")*"?
  | ;
  | [^;'"$\-/Ee]+
  | .
    """,
    re.X | re.S,
)


def split_statements(sql: str, keep_comments: bool = False) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    for m in _PIECE.finditer(sql):
        piece = m.group()
        if piece == ";":
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
        elif not keep_comments and (piece.startswith("--") or piece.startswith("/*")):
            buf.append(" ")
        else:
            buf.append(piece)
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out
