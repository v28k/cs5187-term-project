"""Parser for the ``.pgg`` grammar format.

A ``.pgg`` file is a typed context-free grammar for SQL::

    %type int  "int"  num ord w=5        # type name, SQL spelling, classes, weight
    %start stmt                          # default start rule

    expr<T>          : <4> @col(T) | <3> @lit(T) | "(" expr<T> ")" ;
    expr<T:num>      : expr<T> "+" expr<T> ;
    expr<bool>       : expr<X> "=" expr<X> | <1 ?agg_ok> agg<bool> ;
    subq<T> @scope @shape(T) : "(" SELECT @items ^from_clause ")" ;

Elements
    ``KEYWORD``        an all-uppercase word is emitted literally
    ``"text"``         quoted text is emitted literally (punctuation must be quoted)
    ``name<type>``     nonterminal, optionally with a type argument
    ``@name(args)``    builtin implemented in Python (scope, columns, literals, ...);
                       the "(" must follow the name without a space
    ``$T``             the SQL spelling of a type variable
    ``( a | b )``      group
    ``x?`` ``x?0.2``   optional (probability 0.5 or the given one)
    ``x*`` ``x+``      0..3 / 1..3 repetitions
    ``x{m,n}`` ``x{m,n/","}``   m..n repetitions, optionally separated
    ``^x``             expand ``x`` before the other elements (rendering order is unchanged),
                       e.g. FROM before the select list so the list can refer to its columns

Type arguments
    ``T``              the rule's type parameter
    ``int``            a declared type
    ``num``            a declared class: a fresh random member at every use
    ``X`` ``X:num``    an alternative-local type variable, bound at first use
    ``*`` ``*:num``    any type (of a class), fresh at every use

Alternative annotations ``<w ?flag ?!flag>``: weight, required and forbidden context flags.
Rule attributes (``@scope``, ``@scope(isolated)``, ``@scope(lateral)``, ``@set(f,..)``,
``@clear(f,..)``, ``@shape``, ``@shape(T)``, ``@frame``) apply to every variant of a rule name.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path


class GrammarError(ValueError):
    pass


# ---------------------------------------------------------------- AST

@dataclass(frozen=True)
class TypeArg:
    kind: str           # "param" | "concrete" | "class" | "local" | "any"
    name: str = ""      # param / type / class / variable name
    cls: str = ""       # class constraint for "local" and "any" ("" = all types)

    def __str__(self) -> str:
        if self.kind == "any":
            return "*" + (f":{self.cls}" if self.cls else "")
        return self.name + (f":{self.cls}" if self.cls and self.kind == "local" else "")


@dataclass
class Lit:
    text: str


@dataclass
class NT:
    name: str
    targ: TypeArg | None = None


@dataclass
class Builtin:
    name: str
    args: list[str] = field(default_factory=list)


@dataclass
class TypeName:
    var: str


@dataclass
class Group:
    alts: list["Alt"]


@dataclass
class Repeat:
    elem: object
    lo: int
    hi: int
    sep: str | None = None
    p: float | None = None     # for optionals (lo=0, hi=1)


_uid = itertools.count(1)


@dataclass
class Alt:
    elems: list[object]
    weight: float = 1.0
    require: frozenset[str] = frozenset()
    forbid: frozenset[str] = frozenset()
    early: frozenset[int] = frozenset()        # element indices marked with ^
    uid: int = field(default_factory=lambda: next(_uid))
    line: int = 0
    mind: dict = field(default_factory=dict)   # type -> minimal derivation depth (filled by Grammar)


@dataclass
class Variant:
    name: str
    param: str | None            # type parameter name
    pclass: str | None           # T:num   -> "num"
    concrete: str | None         # expr<int> -> "int"
    alts: list[Alt]
    line: int = 0

    def matches(self, typ: str | None, grammar: "Grammar") -> bool:
        if self.concrete is not None:
            return typ == self.concrete
        if self.param is None:
            return typ is None
        if typ is None:
            return False
        return self.pclass is None or typ in grammar.classes.get(self.pclass, ())


@dataclass
class TypeDecl:
    name: str
    sql: str
    classes: list[str]
    weight: float = 1.0


@dataclass
class Grammar:
    types: dict[str, TypeDecl]
    classes: dict[str, list[str]]
    rules: dict[str, list[Variant]]
    attrs: dict[str, dict[str, list[str]]]
    start: str = "stmt"
    source: str = ""

    def candidates(self, name: str, typ: str | None) -> list[tuple[Variant, Alt]]:
        return [(v, a) for v in self.rules.get(name, ()) if v.matches(typ, self) for a in v.alts]

    def class_members(self, cls: str) -> list[str]:
        return list(self.types) if not cls else self.classes.get(cls, [])

    def stats(self) -> dict[str, int]:
        return {"rules": len(self.rules), "variants": sum(map(len, self.rules.values())),
                "alternatives": sum(len(v.alts) for vs in self.rules.values() for v in vs),
                "types": len(self.types)}


# ---------------------------------------------------------------- lexer

_TOK = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<comment>(?:\#|--)[^\n]*)
  | (?P<directive>%[a-z_]+)
  | (?P<string>"(?:[^"\n])*"|'(?:[^'\n])*')
  | (?P<number>\d+(?:\.\d+)?)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<punct>[:|;()?*+{}<>,/^@$=!\-\[\]])
    """,
    re.VERBOSE,
)


@dataclass
class Tok:
    kind: str
    text: str
    line: int
    pos: int = 0
    end: int = 0


def _lex(text: str) -> list[Tok]:
    toks: list[Tok] = []
    pos, line = 0, 1
    while pos < len(text):
        m = _TOK.match(text, pos)
        if not m:
            raise GrammarError(f"line {line}: unexpected character {text[pos]!r}")
        kind = m.lastgroup or ""
        s = m.group()
        if kind not in ("ws", "comment"):
            toks.append(Tok(kind, s, line, m.start(), m.end()))
        line += s.count("\n")
        pos = m.end()
    toks.append(Tok("eof", "", line, pos, pos))
    return toks


_KEYWORD = re.compile(r"^[A-Z][A-Z0-9_]*$")


# ---------------------------------------------------------------- parser

class _Parser:
    def __init__(self, text: str) -> None:
        self.toks = _lex(text)
        self.i = 0

    # helpers
    def peek(self, k: int = 0) -> Tok:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def next(self) -> Tok:
        t = self.toks[self.i]
        self.i += 1
        return t

    def at(self, text: str, k: int = 0) -> bool:
        t = self.peek(k)
        return t.kind == "punct" and t.text == text

    def expect(self, text: str) -> Tok:
        t = self.next()
        if t.kind != "punct" or t.text != text:
            raise GrammarError(f"line {t.line}: expected {text!r}, got {t.text or t.kind!r}")
        return t

    def ident(self) -> str:
        t = self.next()
        if t.kind != "ident":
            raise GrammarError(f"line {t.line}: expected a name, got {t.text or t.kind!r}")
        return t.text

    # top level
    def parse(self) -> tuple[list[TypeDecl], list[Variant], dict[str, dict[str, list[str]]], str | None]:
        types: list[TypeDecl] = []
        variants: list[Variant] = []
        attrs: dict[str, dict[str, list[str]]] = {}
        start = None
        while self.peek().kind != "eof":
            t = self.peek()
            if t.kind == "directive":
                self.next()
                if t.text == "%type":
                    types.append(self._typedecl(t.line))
                elif t.text == "%start":
                    start = self.ident()
                else:
                    raise GrammarError(f"line {t.line}: unknown directive {t.text}")
                continue
            variants.append(self._rule(attrs))
        return types, variants, attrs, start

    def _typedecl(self, line: int) -> TypeDecl:
        name = self.ident()
        s = self.next()
        if s.kind != "string":
            raise GrammarError(f"line {line}: %type {name} needs a quoted SQL spelling")
        classes, weight = [], 1.0
        while self.peek().kind == "ident" and self.peek().line == line:
            word = self.ident()
            if word == "w" and self.at("="):
                self.next()
                weight = float(self.next().text)
            else:
                classes.append(word)
        return TypeDecl(name, s.text[1:-1], classes, weight)

    def _rule(self, attrs: dict[str, dict[str, list[str]]]) -> Variant:
        line = self.peek().line
        name = self.ident()
        param = pclass = concrete = None
        if self.at("<"):
            self.next()
            first = self.ident()
            if self.at(":"):
                self.next()
                param, pclass = first, self.ident()
            elif len(first) == 1 and first.isupper():
                param = first
            else:
                concrete = first          # resolved against %type / class later
            self.expect(">")
        rattrs = attrs.setdefault(name, {})
        while self.at("@"):
            self.next()
            a = self.ident()
            args: list[str] = []
            if self.at("("):
                self.next()
                while not self.at(")"):
                    args.append(self.next().text)
                    if self.at(","):
                        self.next()
                self.expect(")")
            rattrs.setdefault(a, [])
            rattrs[a] = rattrs[a] + [x for x in args if x not in rattrs[a]]
        self.expect(":")
        alts = self._alts(stop=";")
        self.expect(";")
        return Variant(name, param, pclass, concrete, alts, line)

    def _alts(self, stop: str) -> list[Alt]:
        alts = [self._alt(stop)]
        while self.at("|"):
            self.next()
            alts.append(self._alt(stop))
        return alts

    def _alt(self, stop: str) -> Alt:
        line = self.peek().line
        weight, req, forb = 1.0, set(), set()
        if self.at("<"):
            self.next()
            while not self.at(">"):
                t = self.next()
                if t.kind == "number":
                    weight = float(t.text)
                elif t.text == "?":
                    if self.at("!"):
                        self.next()
                        forb.add(self.ident())
                    else:
                        req.add(self.ident())
                else:
                    raise GrammarError(f"line {t.line}: bad alternative annotation {t.text!r}")
            self.next()
        elems, early = [], set()
        while not (self.at("|") or self.at(stop) or self.peek().kind == "eof"):
            if self.at("^"):
                self.next()
                early.add(len(elems))
            elems.append(self._postfix(self._primary()))
        return Alt(elems, weight, frozenset(req), frozenset(forb), frozenset(early), line=line)

    def _targ(self) -> TypeArg:
        if self.at("*"):
            self.next()
            cls = ""
            if self.at(":"):
                self.next()
                cls = self.ident()
            return TypeArg("any", "", cls)
        name = self.ident()
        cls = ""
        if self.at(":"):
            self.next()
            cls = self.ident()
        return TypeArg("unresolved", name, cls)

    def _primary(self) -> object:
        t = self.peek()
        if t.kind == "string":
            self.next()
            return Lit(t.text[1:-1])
        if t.kind == "ident":
            self.next()
            if _KEYWORD.match(t.text) and not self.at("<"):
                return Lit(t.text)
            targ = None
            if self.at("<"):
                self.next()
                targ = self._targ()
                self.expect(">")
            return NT(t.text, targ)
        if self.at("@"):
            self.next()
            name_tok = self.peek()
            name = self.ident()
            args: list[str] = []
            # arguments only when "(" follows the name directly: "@ordinal (ASC | DESC)" is a group
            if self.at("(") and self.peek().pos == name_tok.end:
                self.next()
                while not self.at(")"):
                    a = self.next()
                    text = a.text
                    if a.kind == "string":
                        text = a.text[1:-1]
                    elif text == "*" and self.at(":"):
                        self.next()
                        text = "*:" + self.ident()
                    elif a.kind == "ident" and self.at(":"):
                        self.next()
                        text = text + ":" + self.ident()
                    args.append(text)
                    if self.at(","):
                        self.next()
                self.expect(")")
            return Builtin(name, args)
        if self.at("$"):
            self.next()
            return TypeName(self.ident())
        if self.at("("):
            self.next()
            alts = self._alts(stop=")")
            self.expect(")")
            return Group(alts)
        raise GrammarError(f"line {t.line}: unexpected {t.text or t.kind!r}")

    def _postfix(self, el: object) -> object:
        while True:
            if self.at("?"):
                self.next()
                p = None
                if self.peek().kind == "number":
                    p = float(self.next().text)
                el = Repeat(el, 0, 1, None, p)
            elif self.at("*"):
                self.next()
                el = Repeat(el, 0, 3)
            elif self.at("+"):
                self.next()
                el = Repeat(el, 1, 3)
            elif self.at("{"):
                self.next()
                lo = int(self.next().text)
                hi = lo
                if self.at(","):
                    self.next()
                    hi = int(self.next().text)
                sep = None
                if self.at("/"):
                    self.next()
                    s = self.next()
                    sep = s.text[1:-1] if s.kind == "string" else s.text
                self.expect("}")
                el = Repeat(el, lo, hi, sep)
            else:
                return el


# ---------------------------------------------------------------- linking

def _walk(elems: list[object]):
    for el in elems:
        yield el
        if isinstance(el, Repeat):
            yield from _walk([el.elem])
        elif isinstance(el, Group):
            for a in el.alts:
                yield from _walk(a.elems)


def _alts_of(variant: Variant):
    stack = list(variant.alts)
    while stack:
        a = stack.pop()
        yield a
        for el in _walk(a.elems):
            if isinstance(el, Group):
                stack.extend(el.alts)


def _resolve(g: Grammar, v: Variant) -> None:
    def fix(targ: TypeArg | None, line: int) -> TypeArg | None:
        if targ is None or targ.kind != "unresolved":
            if targ is not None and targ.kind == "any" and targ.cls and targ.cls not in g.classes:
                raise GrammarError(f"line {line}: unknown type class {targ.cls!r}")
            return targ
        n = targ.name
        if n == v.param:
            return TypeArg("param", n)
        if n in g.types:
            return TypeArg("concrete", n)
        if n in g.classes:
            return TypeArg("class", n)
        if targ.cls and targ.cls not in g.classes:
            raise GrammarError(f"line {line}: unknown type class {targ.cls!r}")
        return TypeArg("local", n, targ.cls)

    if v.concrete is not None and v.concrete not in g.types:
        raise GrammarError(f"line {v.line}: {v.name}<{v.concrete}>: unknown type")
    if v.pclass is not None and v.pclass not in g.classes:
        raise GrammarError(f"line {v.line}: unknown type class {v.pclass!r}")
    for a in _alts_of(v):
        for el in _walk(a.elems):
            if isinstance(el, NT):
                if el.name not in g.rules:
                    raise GrammarError(f"line {a.line}: undefined rule {el.name!r}")
                el.targ = fix(el.targ, a.line)


def _compute_mind(g: Grammar) -> None:
    """Minimal derivation depth of every (rule, type) and alternative, used to
    steer expansions towards termination near the depth limit."""
    INF = 10**6
    typs: list[str | None] = [None, *g.types]
    best: dict[tuple[str, str | None], int] = {}

    def nt_cost(el: NT, bound: dict[str, str]) -> int:
        if el.targ is None:
            return best.get((el.name, None), INF)
        k = el.targ.kind
        if k in ("param", "concrete"):
            t = bound.get(el.targ.name) if k == "param" else el.targ.name
            return best.get((el.name, t), INF)
        members = g.class_members(el.targ.cls if k in ("local", "any") else el.targ.name)
        return min((best.get((el.name, t), INF) for t in members), default=INF)

    def cost(elems: list[object], bound: dict[str, str]) -> int:
        worst = 0
        for el in elems:
            if isinstance(el, NT):
                c = nt_cost(el, bound)
            elif isinstance(el, Repeat):
                c = 0 if el.lo == 0 else cost([el.elem], bound)
            elif isinstance(el, Group):
                c = min(cost(a.elems, bound) for a in el.alts)
            else:
                c = 0
            worst = max(worst, c)
        return worst

    changed = True
    while changed:
        changed = False
        for name, variants in g.rules.items():
            for t in typs:
                for v in variants:
                    if not v.matches(t, g):
                        continue
                    bound = {v.param: t} if v.param and t else {}
                    for a in v.alts:
                        c = 1 + cost(a.elems, bound)
                        if c < a.mind.get(t, INF):
                            a.mind[t] = c
                        if c < best.get((name, t), INF):
                            best[(name, t)] = c
                            changed = True


def parse_grammar(text: str, source: str = "") -> Grammar:
    types, variants, attrs, start = _Parser(text).parse()
    tmap = {t.name: t for t in types}
    classes: dict[str, list[str]] = {}
    for t in types:
        for c in t.classes:
            classes.setdefault(c, []).append(t.name)
    if set(tmap) & set(classes):
        raise GrammarError(f"names used both as type and class: {sorted(set(tmap) & set(classes))}")
    rules: dict[str, list[Variant]] = {}
    for v in variants:
        rules.setdefault(v.name, []).append(v)
    g = Grammar(tmap, classes, rules, attrs, start or "stmt", source)
    if g.start not in rules:
        raise GrammarError(f"start rule {g.start!r} is not defined")
    for vs in rules.values():
        for v in vs:
            _resolve(g, v)
    _compute_mind(g)
    return g


def load_grammar(path: str | Path) -> Grammar:
    p = Path(path)
    return parse_grammar(p.read_text(encoding="utf-8"), str(p))
