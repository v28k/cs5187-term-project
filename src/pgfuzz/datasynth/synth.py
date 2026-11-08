"""Rows that make each partition of a predicate non-empty.

A TLP check compares a query with the union of its WHERE predicate's TRUE, FALSE and NULL
partitions. On random data most partitions are empty, and a check whose sides are both empty
says nothing (it is *vacuous*). Here the predicate's text is parsed into a small expression tree,
encoded in Z3 under SQL's three-valued logic, and solved once per outcome; each model gives one
row per table alias, inserted before the query. Everything the encoder does not understand
(function calls, CASE, subqueries, casts between type families, ``/``, ``%``) becomes a fresh,
unconstrained value, so unsupported syntax never makes a predicate unsolvable, it only makes the
rows less likely to land in the intended partition.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any

from pgfuzz.grammar.schema import Schema

INT_TYPES = {"int", "bigint", "smallint", "int2", "int4", "int8", "integer"}
REAL_TYPES = {"numeric", "float8", "float4", "real", "double", "decimal"}
TEXT_TYPES = {"text", "varchar", "char", "string"}
BOOL_TYPES = {"bool", "boolean"}

_TOKEN = re.compile(r"""\s*(?:
    (?P<str>'(?:[^']|'')*')
  | (?P<num>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)
  | (?P<op>::|<>|!=|<=|>=|\|\||[-+*/%=<>(),\[\]{}:;.])
)""", re.X)

_CMP = {"=", "<>", "!=", "<", ">", "<=", ">="}
_KEYWORDS = {"AND", "OR", "NOT", "IS", "NULL", "TRUE", "FALSE", "BETWEEN", "IN", "LIKE", "CASE",
             "END", "SELECT", "CAST", "AS", "ARRAY", "EXISTS", "ANY", "ALL", "SOME"}


def tokenize(sql: str) -> list[str]:
    out, pos = [], 0
    while pos < len(sql):
        m = _TOKEN.match(sql, pos)
        if m is None or m.end() == pos:
            if sql[pos:].strip():
                out.append(sql[pos])     # unknown character: an opaque token
                pos += 1
                continue
            break
        out.append(m.group(m.lastgroup))  # type: ignore[arg-type]
        pos = m.end()
    return out


# ------------------------------------------------------------------ expression trees
#   ("lit", kind, value)  kind in int/real/str/bool/null
#   ("col", alias, name)
#   ("op", op, a, b)       arithmetic / comparison / AND / OR / ||
#   ("not", a) ("neg", a) ("isnull", a, negated) ("istruth", a, value, negated)
#   ("between", a, lo, hi, negated) ("in", a, [items], negated) ("like", a, pattern, negated)
#   ("cast", a, type) ("opaque",)

class _Parser:
    def __init__(self, toks: list[str]) -> None:
        self.t, self.i = toks, 0

    def peek(self, k: int = 0) -> str:
        j = self.i + k
        return self.t[j] if j < len(self.t) else ""

    def up(self, k: int = 0) -> str:
        return self.peek(k).upper()

    def take(self) -> str:
        tok = self.peek()
        self.i += 1
        return tok

    def skip_balanced(self) -> None:
        """Skip one bracketed group starting at the current '(' / '[' / '{'."""
        depth = 0
        while self.i < len(self.t):
            tok = self.take()
            if tok in "([{":
                depth += 1
            elif tok in ")]}":
                depth -= 1
                if depth <= 0:
                    return

    def call_args(self) -> list | None:
        """Arguments of a call at '(' (None if they are not plain expressions)."""
        self.take()
        if self.peek() == ")":
            self.take()
            return []
        if self.up() in ("DISTINCT", "ALL", "SELECT", "WITH"):
            return None
        args = [self.expr()]
        while self.peek() == ",":
            self.take()
            args.append(self.expr())
        if self.peek() != ")":
            return None
        self.take()
        return args

    def parse(self):
        e = self.expr()
        return e if self.i >= len(self.t) else ("opaque",)

    def expr(self):
        a = self.conj()
        while self.up() == "OR":
            self.take()
            a = ("op", "OR", a, self.conj())
        return a

    def conj(self):
        a = self.neg()
        while self.up() == "AND":
            self.take()
            a = ("op", "AND", a, self.neg())
        return a

    def neg(self):
        if self.up() == "NOT":
            self.take()
            return ("not", self.neg())
        return self.pred()

    def pred(self):
        a = self.add()
        while True:
            u = self.up()
            if u == "IS":
                self.take()
                negated = self.up() == "NOT"
                if negated:
                    self.take()
                v = self.take().upper()
                if v == "NULL":
                    a = ("isnull", a, negated)
                elif v in ("TRUE", "FALSE"):
                    a = ("istruth", a, v == "TRUE", negated)
                else:                           # IS DISTINCT FROM, IS JSON ...: opaque
                    if v == "DISTINCT" and self.up() == "FROM":
                        self.take()
                        self.add()
                    a = ("opaque",)
            elif u in ("BETWEEN", "IN", "LIKE", "ILIKE") or (u == "NOT" and self.up(1) in ("BETWEEN", "IN", "LIKE", "ILIKE")):
                negated = u == "NOT"
                if negated:
                    self.take()
                kw = self.take().upper()
                if kw == "BETWEEN":
                    if self.up() == "SYMMETRIC":
                        self.take()
                    lo = self.add()
                    if self.up() != "AND":
                        return ("opaque",)
                    self.take()
                    a = ("between", a, lo, self.add(), negated)
                elif kw == "IN":
                    if self.peek() != "(":
                        return ("opaque",)
                    if self.up(1) in ("SELECT", "WITH", "VALUES"):
                        self.skip_balanced()
                        a = ("opaque",)
                        continue
                    self.take()
                    items = [self.add()]
                    while self.peek() == ",":
                        self.take()
                        items.append(self.add())
                    if self.peek() != ")":
                        return ("opaque",)
                    self.take()
                    a = ("in", a, items, negated)
                else:
                    pat = self.add()
                    a = ("like", a, pat, negated) if kw == "LIKE" else ("opaque",)
            elif self.peek() in _CMP:
                op = self.take()
                if self.up() in ("ANY", "ALL", "SOME"):
                    self.take()
                    if self.peek() == "(":
                        self.skip_balanced()
                    a = ("opaque",)
                else:
                    a = ("op", "<>" if op == "!=" else op, a, self.add())
            else:
                return a

    def add(self):
        a = self.mul()
        while self.peek() in ("+", "-", "||"):
            op = self.take()
            a = ("op", op, a, self.mul())
        return a

    def mul(self):
        a = self.unary()
        while self.peek() in ("*", "/", "%"):
            op = self.take()
            b = self.unary()
            a = ("op", "*", a, b) if op == "*" else ("opaque",)
        return a

    def unary(self):
        if self.peek() == "-":
            self.take()
            return ("neg", self.unary())
        if self.peek() == "+":
            self.take()
        return self.postfix()

    def typename(self) -> str:
        name = self.take().lower()
        while self.peek() == "[":
            self.take()
            if self.peek() == "]":
                self.take()
            name += "[]"
        return name

    def postfix(self):
        a = self.primary()
        while self.peek() == "::":
            self.take()
            a = ("cast", a, self.typename())
        while self.peek() == "[":          # subscripts
            self.skip_balanced()
            a = ("opaque",)
        return a

    def primary(self):
        tok = self.peek()
        u = tok.upper()
        if not tok:
            return ("opaque",)
        if tok.startswith("'"):
            self.take()
            return ("lit", "str", tok[1:-1].replace("''", "'"))
        if tok[0].isdigit():
            self.take()
            return ("lit", "int", int(tok)) if re.fullmatch(r"\d+", tok) else ("lit", "real", float(tok))
        if u == "NULL":
            self.take()
            return ("lit", "null", None)
        if u in ("TRUE", "FALSE"):
            self.take()
            return ("lit", "bool", u == "TRUE")
        if tok == "(":
            if self.up(1) in ("SELECT", "WITH", "VALUES"):
                self.skip_balanced()
                return ("opaque",)
            self.take()
            e = self.expr()
            if self.peek() == ",":                    # row constructor
                while self.peek() not in (")", ""):
                    self.take()
                e = ("opaque",)
            if self.peek() == ")":
                self.take()
            return e
        if u == "CAST" and self.peek(1) == "(":
            self.take()
            self.take()
            e = self.expr()
            if self.up() != "AS":
                return ("opaque",)
            self.take()
            typ = self.typename()
            if self.peek() == ")":
                self.take()
            return ("cast", e, typ)
        if u == "CASE":
            self.take()
            operand = None if self.up() == "WHEN" else self.expr()
            arms = []
            while self.up() == "WHEN":
                self.take()
                w = self.expr()
                if self.up() != "THEN":
                    return ("opaque",)
                self.take()
                arms.append((w, self.expr()))
            other = None
            if self.up() == "ELSE":
                self.take()
                other = self.expr()
            if self.up() != "END" or not arms:
                return ("opaque",)
            self.take()
            return ("case", operand, arms, other)
        if u in ("EXISTS", "ARRAY") or tok in ("[", "{"):
            self.take()
            if self.peek() in ("(", "[") or tok in ("[", "{"):
                if tok in ("[", "{"):
                    self.i -= 1
                self.skip_balanced()
            return ("opaque",)
        if re.match(r"[A-Za-z_]", tok):
            self.take()
            if self.peek() == "(":                    # function call
                start = self.i
                args = self.call_args()
                if args is None or self.up() in ("OVER", "FILTER", "WITHIN"):
                    self.i = start
                    self.skip_balanced()
                    return ("opaque",)
                return ("call", u, args)
            if u in _KEYWORDS:
                return ("opaque",)
            if "." in tok:
                alias, name = tok.split(".", 1)
                return ("col", alias, name)
            return ("col", None, tok)
        self.take()
        return ("opaque",)


def parse_predicate(sql: str):
    return _Parser(tokenize(sql)).parse()


def join_conditions(from_sql: str) -> list[str]:
    """The ``ON`` conditions of a FROM clause (text), outermost level of each join."""
    toks = tokenize(from_sql)
    out: list[str] = []
    i = 0
    while i < len(toks):
        if toks[i].upper() != "ON":
            i += 1
            continue
        depth, j = 0, i + 1
        while j < len(toks):
            w = toks[j]
            if w in "([{":
                depth += 1
            elif w in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and (w == "," or w.upper() in ("JOIN", "LEFT", "RIGHT", "FULL", "INNER", "CROSS",
                                                          "NATURAL", "WHERE", "LATERAL", "POSITIONAL", "ASOF")):
                break
            j += 1
        if j > i + 1:
            out.append(" ".join(toks[i + 1:j]))
        i = j
    return out


_TABLE_REF = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)(?:\s+AS\s+([A-Za-z_][A-Za-z0-9_]*))?(?!\s*\(|\.)", re.I)


def alias_map(sql: str, schema: Schema) -> dict[str, str]:
    """``alias -> table`` for the base tables a statement names (``FROM t0 AS a1``: a1 -> t0;
    ``FROM t0``: t0 -> t0)."""
    out: dict[str, str] = {}
    for table, alias in _TABLE_REF.findall(sql):
        r = schema.relations.get(table)
        if r is not None and r.writable:
            out[alias or table] = table
    return out


# ------------------------------------------------------------------ Z3 encoding

@dataclass
class _Val:
    kind: str          # int / real / str / bool / any
    null: Any          # z3 BoolRef
    v: Any = None      # z3 term (None for kind "any")


def _sort_of(typ: str) -> str | None:
    t = typ.lower()
    if t in INT_TYPES:
        return "int"
    if t in REAL_TYPES:
        return "real"
    if t in TEXT_TYPES:
        return "str"
    if t in BOOL_TYPES:
        return "bool"
    return None


class _Encoder:
    def __init__(self, z3: Any, schema: Schema, aliases: dict[str, str]) -> None:
        self.z3, self.schema, self.aliases = z3, schema, aliases
        self.cols: dict[tuple[str, str], tuple[str, _Val]] = {}   # (alias, col) -> (sort, value)
        self.domain: list[Any] = []
        self.keys: list[Any] = []
        self.n = 0

    def fresh(self, kind: str) -> _Val:
        z3 = self.z3
        self.n += 1
        null = z3.Bool(f"_n{self.n}")
        if kind == "any":
            return _Val("any", null)
        return _Val(kind, null, self._var(kind, f"_v{self.n}"))

    def _var(self, kind: str, name: str, key: bool = False):
        z3 = self.z3
        if kind == "int":
            v = z3.Int(name)
            lo, hi = (1000, 1999) if key else (-40, 40)   # keys stay away from the seeded ones
            self.domain.append(z3.And(v >= lo, v <= hi))
            return v
        if kind == "real":                       # quarters: exact decimal literals
            k = z3.Int(name + "_q")
            self.domain.append(z3.And(k >= -400, k <= 400))
            return z3.ToReal(k) / 4
        if kind == "str":
            v = z3.String(name)
            word = z3.Star(z3.Union(z3.Range("a", "z"), z3.Range("0", "9")))
            self.domain.append(z3.And(z3.InRe(v, word), z3.Length(v) <= 6))
            return v
        return z3.Bool(name)

    def column(self, alias: str | None, name: str) -> _Val:
        if alias is None:
            hits = [a for a, t in self.aliases.items() if self.schema.relations[t].col(name)]
            if len(hits) != 1:
                return self.fresh("any")
            alias = hits[0]
        table = self.aliases.get(alias)
        rel = self.schema.relations.get(table) if table else None
        col = rel.col(name) if rel is not None else None
        sort = _sort_of(col.type) if col is not None else None
        if col is None or sort is None or not col.writable:
            return self.fresh("any")
        key = (alias, name)
        if key not in self.cols:
            z3 = self.z3
            null = z3.Bool(f"{alias}.{name}#null")
            if "notnull" in col.flags or "pk" in col.flags:
                self.domain.append(z3.Not(null))
            v = self._var(sort, f"{alias}.{name}", key="pk" in col.flags)
            if "pk" in col.flags:                      # unique per synthesized row
                self.keys.append(v)
            self.cols[key] = (sort, _Val(sort, null, v))
        return self.cols[key][1]

    # ---- helpers
    def as_kind(self, x: _Val, kind: str) -> _Val:
        if x.kind == kind:
            return x
        if x.kind == "any":
            return _Val(kind, x.null, self._var(kind, f"_a{id(x)}_{self.n}"))
        if x.kind == "int" and kind == "real":
            return _Val("real", x.null, self.z3.ToReal(x.v))
        return self.fresh(kind)

    def unify(self, a: _Val, b: _Val) -> tuple[_Val, _Val] | None:
        if a.kind == "any" and b.kind == "any":
            return None
        if a.kind == "any":
            return self.as_kind(a, b.kind), b
        if b.kind == "any":
            return a, self.as_kind(b, a.kind)
        if a.kind == b.kind:
            return a, b
        if {a.kind, b.kind} == {"int", "real"}:
            return self.as_kind(a, "real"), self.as_kind(b, "real")
        return None

    def truth(self, x: _Val):
        z3 = self.z3
        x = self.as_kind(x, "bool")
        return z3.And(z3.Not(x.null), x.v), z3.And(z3.Not(x.null), z3.Not(x.v))

    def from_truth(self, t, f) -> _Val:
        z3 = self.z3
        return _Val("bool", z3.And(z3.Not(t), z3.Not(f)), t)

    # ---- encoding
    def enc(self, e) -> _Val:
        z3 = self.z3
        tag = e[0]
        if tag == "lit":
            kind, val = e[1], e[2]
            if kind == "null":
                return _Val("any", z3.BoolVal(True))
            if kind == "int":
                return _Val("int", z3.BoolVal(False), z3.IntVal(val))
            if kind == "real":
                return _Val("real", z3.BoolVal(False), z3.RealVal(str(val)))
            if kind == "str":
                return _Val("str", z3.BoolVal(False), z3.StringVal(val))
            return _Val("bool", z3.BoolVal(False), z3.BoolVal(val))
        if tag == "col":
            return self.column(e[1], e[2])
        if tag == "cast":
            x, sort = self.enc(e[1]), _sort_of(e[2])
            if sort is None:
                return self.fresh("any")
            if e[1][0] == "lit" and e[1][1] == "str" and sort in ("int", "real"):
                try:
                    num = float(e[1][2])
                except ValueError:
                    return self.fresh(sort)
                if sort == "int" and num.is_integer():
                    return _Val("int", z3.BoolVal(False), z3.IntVal(int(num)))
                return _Val("real", z3.BoolVal(False), z3.RealVal(str(num))) if sort == "real" else self.fresh(sort)
            if e[1][0] == "lit" and e[1][1] == "str" and sort == "bool":
                s = str(e[1][2]).strip().lower()
                if s in ("t", "true", "yes", "on", "1", "f", "false", "no", "off", "0"):
                    return _Val("bool", z3.BoolVal(False), z3.BoolVal(s in ("t", "true", "yes", "on", "1")))
            if x.kind == sort or x.kind == "any":
                return self.as_kind(x, sort)
            if x.kind == "int" and sort == "real":
                return self.as_kind(x, "real")
            return self.fresh(sort)
        if tag == "neg":
            x = self.enc(e[1])
            if x.kind in ("int", "real"):
                return _Val(x.kind, x.null, -x.v)
            return self.fresh("any")
        if tag == "not":
            t, f = self.truth(self.enc(e[1]))
            return self.from_truth(f, t)
        if tag == "isnull":
            x = self.enc(e[1])
            return _Val("bool", z3.BoolVal(False), z3.Not(x.null) if e[2] else x.null)
        if tag == "istruth":
            t, f = self.truth(self.enc(e[1]))
            hit = t if e[2] else f
            return _Val("bool", z3.BoolVal(False), z3.Not(hit) if e[3] else hit)
        if tag == "between":
            lo = ("op", ">=", e[1], e[2])
            hi = ("op", "<=", e[1], e[3])
            r = self.enc(("op", "AND", lo, hi))
            if e[4]:
                t, f = self.truth(r)
                return self.from_truth(f, t)
            return r
        if tag == "in":
            if not e[2]:
                return self.fresh("bool")
            r = self.enc(("op", "=", e[1], e[2][0]))
            for item in e[2][1:]:
                t1, f1 = self.truth(r)
                t2, f2 = self.truth(self.enc(("op", "=", e[1], item)))
                r = self.from_truth(z3.Or(t1, t2), z3.And(f1, f2))
            if e[3]:
                t, f = self.truth(r)
                return self.from_truth(f, t)
            return r
        if tag == "like":
            x = self.enc(e[1])
            x = self.as_kind(x, "str") if x.kind in ("str", "any") else None
            pat = e[2]
            if x is None or pat[0] != "lit" or pat[1] != "str":
                return self.fresh("bool")
            parts = []
            for ch in str(pat[2]):
                if ch == "%":
                    parts.append(z3.Star(z3.Union(z3.Range("a", "z"), z3.Range("0", "9"))))
                elif ch == "_":
                    parts.append(z3.Union(z3.Range("a", "z"), z3.Range("0", "9")))
                else:
                    parts.append(z3.Re(ch))
            if not parts:
                re_ = z3.Re("")
            else:
                re_ = parts[0] if len(parts) == 1 else z3.Concat(*parts)
            hit = z3.InRe(x.v, re_)
            return _Val("bool", x.null, z3.Not(hit) if e[3] else hit)
        if tag == "op":
            op = e[1]
            if op in ("AND", "OR"):
                t1, f1 = self.truth(self.enc(e[2]))
                t2, f2 = self.truth(self.enc(e[3]))
                if op == "AND":
                    return self.from_truth(z3.And(t1, t2), z3.Or(f1, f2))
                return self.from_truth(z3.Or(t1, t2), z3.And(f1, f2))
            a, b = self.enc(e[2]), self.enc(e[3])
            null = z3.Or(a.null, b.null)
            if op == "||":
                if a.kind in ("str", "any") and b.kind in ("str", "any") and not (a.kind == b.kind == "any"):
                    a, b = self.as_kind(a, "str"), self.as_kind(b, "str")
                    return _Val("str", null, z3.Concat(a.v, b.v))
                return self.fresh("any")
            pair = self.unify(a, b)
            if op in _CMP:
                if pair is None:
                    return _Val("bool", null, z3.Bool(f"_c{id(e)}_{self.n}"))
                a, b = pair
                if a.kind == "bool" and op not in ("=", "<>"):
                    return _Val("bool", null, z3.Bool(f"_c{id(e)}_{self.n}"))
                v = {"=": a.v == b.v, "<>": a.v != b.v, "<": a.v < b.v if a.kind != "bool" else None,
                     ">": a.v > b.v if a.kind != "bool" else None, "<=": a.v <= b.v if a.kind != "bool" else None,
                     ">=": a.v >= b.v if a.kind != "bool" else None}[op]
                return _Val("bool", null, v)
            if pair is None or pair[0].kind not in ("int", "real"):
                return self.fresh("any")
            a, b = pair
            v = {"+": a.v + b.v, "-": a.v - b.v, "*": a.v * b.v}[op]
            return _Val(a.kind, null, v)
        if tag == "case":
            return self.case(e)
        if tag == "call":
            return self.call(e[1], e[2])
        return self.fresh("any")

    def merge(self, vals: list[_Val]) -> list[_Val] | None:
        """Bring values to one sort (None if they have none in common)."""
        kinds = {v.kind for v in vals} - {"any"}
        if not kinds:
            return None
        kind = "real" if kinds == {"int", "real"} else kinds.pop() if len(kinds) == 1 else None
        return [self.as_kind(v, kind) for v in vals] if kind else None

    def ite(self, cond, a: _Val, b: _Val) -> _Val:
        z3 = self.z3
        return _Val(a.kind, z3.If(cond, a.null, b.null), z3.If(cond, a.v, b.v))

    def case(self, e) -> _Val:
        z3 = self.z3
        operand = self.enc(e[1]) if e[1] is not None else None
        conds = []
        for w, _ in e[2]:
            c = self.enc(w if operand is None else ("op", "=", e[1], w))
            conds.append(self.truth(c)[0])
        vals = [self.enc(t) for _, t in e[2]] + [self.enc(e[3]) if e[3] is not None else _Val("any", z3.BoolVal(True))]
        merged = self.merge(vals)
        if merged is None:
            return self.fresh("any")
        out = merged[-1]
        for cond, v in zip(reversed(conds), reversed(merged[:-1])):
            out = self.ite(cond, v, out)
        return out

    def call(self, name: str, args: list) -> _Val:
        z3 = self.z3
        vals = [self.enc(a) for a in args]          # registers the columns the arguments read
        if name == "COALESCE" and vals:
            merged = self.merge(vals)
            if merged is None:
                return self.fresh("any")
            out = merged[-1]
            for v in reversed(merged[:-1]):
                out = self.ite(z3.Not(v.null), v, out)
            return out
        if name == "NULLIF" and len(vals) == 2:
            merged = self.merge(vals)
            if merged is None:
                return self.fresh("any")
            a, b = merged
            same = z3.And(z3.Not(a.null), z3.Not(b.null), a.v == b.v)
            return _Val(a.kind, z3.Or(a.null, same), a.v)
        if name == "ABS" and len(vals) == 1 and vals[0].kind in ("int", "real"):
            a = vals[0]
            return _Val(a.kind, a.null, z3.If(a.v < 0, -a.v, a.v))
        if name in ("LOWER", "UPPER", "TRIM", "LTRIM", "RTRIM", "MD5", "CONCAT"):
            return self.fresh("str")
        if name in ("LENGTH", "CHAR_LENGTH", "STRLEN"):
            return self.fresh("int")
        return self.fresh("any")

    def cover(self, aliases: dict[str, str]) -> None:
        """Give every table alias at least one column, so each table gets a row."""
        used = {a for a, _ in self.cols}
        for alias, table in aliases.items():
            if alias in used:
                continue
            for c in self.schema.relations[table].columns:
                if c.writable and _sort_of(c.type):
                    self.column(alias, c.name)
                    break


def _render(sort: str, value: Any) -> str:
    if sort == "int":
        return str(value.as_long())
    if sort == "real":
        frac = value.as_fraction()
        return repr(float(frac))
    if sort == "str":
        return "'" + value.as_string().replace("'", "''") + "'"
    return "TRUE" if value.sexpr() == "true" else "FALSE"


class DataSynth:
    """Synthesize INSERT statements that make a predicate TRUE, FALSE and NULL on some row."""

    OUTCOMES = ("true", "false", "null")

    def __init__(self, schema: Schema, rng: random.Random | None = None, timeout_ms: int = 300) -> None:
        import z3

        self.z3, self.schema = z3, schema
        self.rng = rng or random.Random(0)
        self.timeout_ms = timeout_ms
        self.stats = {"predicates": 0, "unsupported": 0, "solved": 0, "unsat": 0, "rows": 0, "joins_kept": 0}

    def rows(self, predicate: str, sql: str, from_sql: str | None = None) -> list[tuple[str, dict[str, str]]]:
        """``(table, {column: literal})`` rows, one per alias and solvable outcome. The ``ON``
        conditions of ``from_sql`` are made TRUE too where possible, so the rows survive the joins."""
        self.stats["predicates"] += 1
        tree = parse_predicate(predicate)
        aliases = alias_map(sql, self.schema)
        enc = _Encoder(self.z3, self.schema, aliases)
        try:
            val = enc.enc(tree)
            t, f = enc.truth(val)
            nul = self.z3.Not(self.z3.Or(t, f))
            joins = [enc.truth(enc.enc(parse_predicate(c)))[0] for c in join_conditions(from_sql or "")]
            enc.cover(aliases)
        except (self.z3.Z3Exception, TypeError, AttributeError):
            self.stats["unsupported"] += 1
            return []
        if not enc.cols:
            self.stats["unsupported"] += 1
            return []
        out: list[tuple[str, dict[str, str]]] = []
        blocked: list[Any] = []
        for goal in (t, f, nul):
            s = self.z3.Solver()
            s.set("timeout", self.timeout_ms)
            s.add(*enc.domain, *blocked, goal)
            if joins:
                s.push()
                s.add(*joins)
                if s.check() == self.z3.sat:
                    self.stats["joins_kept"] += 1
                else:
                    s.pop()
            if s.check() != self.z3.sat:
                self.stats["unsat"] += 1
                continue
            self.stats["solved"] += 1
            m = s.model()
            blocked += [k != m.eval(k, model_completion=True) for k in enc.keys]
            per_alias: dict[str, dict[str, str]] = {}
            for (alias, col), (sort, v) in enc.cols.items():
                is_null = self.z3.is_true(m.eval(v.null, model_completion=True))
                lit = "NULL" if is_null else _render(sort, m.eval(v.v, model_completion=True))
                per_alias.setdefault(alias, {})[col] = lit
            for alias, cols in per_alias.items():
                out.append((aliases[alias], cols))
        self.stats["rows"] += len(out)
        return out

    def inserts(self, predicate: str, sql: str, from_sql: str | None = None) -> list[str]:
        stmts = []
        for table, cols in self.rows(predicate, sql, from_sql):
            rel = self.schema.relations[table]
            full = dict(cols)
            for c in rel.columns:                     # required columns the predicate does not read
                if c.name in full or not c.writable:
                    continue
                if "pk" in c.flags or "notnull" in c.flags:
                    sort = _sort_of(c.type)
                    if sort == "int":
                        full[c.name] = str(self.rng.randrange(100000, 999999))
                    elif sort == "str":
                        full[c.name] = f"'s{self.rng.randrange(100000)}'"
                    elif sort == "real":
                        full[c.name] = "0.5"
                    elif sort == "bool":
                        full[c.name] = "TRUE"
                    else:
                        full = {}
                        break
            if full:
                names = ", ".join(full)
                stmts.append(f"INSERT INTO {table} ({names}) VALUES ({', '.join(full.values())})")
        return stmts
