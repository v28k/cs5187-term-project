"""Derivation engine for ``.pgg`` grammars.

Generation is top-down with backtracking: an alternative that cannot be
completed in the current context (no column of the requested type, depth
limit, ...) raises :class:`Fail` and the next alternative is tried, after
restoring the scope to its state before the attempt.

Every statement is recorded as a derivation tree of :class:`Node`. A tree can
be *replayed* as a guide: at every position the guided choice (alternative,
repetition count, column, literal, ...) is reused if it is still valid in the
current context, otherwise a fresh choice is made. Mutation therefore never
produces dangling references: replacing a subtree (or dropping it to force a
fresh choice) and replaying re-binds everything around it.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any, Callable

from pgfuzz.grammar.dsl import NT, Alt, Builtin, Grammar, Group, Lit, Repeat, TypeArg, TypeName, Variant
from pgfuzz.grammar.schema import Column, Relation, Schema


class Fail(Exception):
    """The current alternative cannot be completed in this context."""


INF = 10**6


@dataclass
class Item:
    """A FROM-clause entry visible to column references."""

    alias: str
    rel: str
    columns: list[Column]
    hidden: bool = False


class Scope:
    """One query level."""

    def __init__(self, parent: "Scope | None" = None, col_parent: "Scope | None" = None) -> None:
        self.parent = parent            # relation (CTE) visibility
        self.col_parent = col_parent    # column visibility (None: isolated)
        self.items: list[Item] = []
        self.rels: list[Relation] = []
        self.grouped = False
        self.group_cols: set[tuple[str, str]] = set()
        self.out: list[str] | None = None
        self.target: Item | None = None
        self.newrel: Relation | None = None
        self.used_cols: set[str] = set()

    def snapshot(self) -> tuple:
        return (len(self.items), len(self.rels), self.grouped, set(self.group_cols), self.out,
                self.target, self.newrel, len(self.newrel.columns) if self.newrel else 0,
                set(self.used_cols))

    def restore(self, s: tuple) -> None:
        n_items, n_rels, self.grouped, self.group_cols, self.out, self.target, self.newrel, n_cols, self.used_cols = s
        del self.items[n_items:]
        del self.rels[n_rels:]
        if self.newrel is not None:
            del self.newrel.columns[n_cols:]


@dataclass(frozen=True)
class Ctx:
    scope: Scope
    flags: frozenset[str] = frozenset()
    shape: tuple[str, ...] | None = None
    frame: tuple[Scope, int] | None = None   # JOIN ... ON may only see items from here on
    depth: int = 0


@dataclass
class Node:
    sym: str                       # rule name, "@builtin", "#rep" or "#grp"
    typ: str | None = None
    alt: int = 0                   # Alt.uid for rules and groups
    kids: list["Node | None"] = field(default_factory=list)
    val: Any = None                # builtin choice / repetition count / shape
    tv: dict[str, str] | None = None
    nid: int = field(default=-1, compare=False, repr=False)   # id of its span markers in the tokens

    def walk(self, path: tuple[int, ...] = ()):
        yield path, self
        for i, k in enumerate(self.kids):
            if k is not None:
                yield from k.walk(path + (i,))

    def size(self) -> int:
        return 1 + sum(k.size() for k in self.kids if k is not None)


def node_at(root: Node, path: tuple[int, ...]) -> Node:
    n = root
    for i in path:
        n = n.kids[i]  # type: ignore[assignment]
    return n


def replace_at(root: Node, path: tuple[int, ...], new: Node | None) -> Node | None:
    """Copy of ``root`` with the subtree at ``path`` replaced (``None``: regenerate)."""
    if not path:
        return new
    kids = list(root.kids)
    kids[path[0]] = replace_at(root.kids[path[0]], path[1:], new)  # type: ignore[arg-type]
    return replace(root, kids=kids)


# ------------------------------------------------------------------ spans
#
# The engine brackets the tokens of every rule node and every builtin node with
# invisible markers ("\x01<nid>" ... "\x02<nid>"). They let tree-level
# operations (metamorphic rewrites, reduction) find exactly the tokens a typed
# node produced, and replace them, without re-parsing SQL. ``render`` drops them.

_OPEN, _CLOSE = "\x01", "\x02"


def is_marker(t: str) -> bool:
    return bool(t) and t[0] in (_OPEN, _CLOSE)


def strip_markers(tokens: list[str]) -> list[str]:
    return [t for t in tokens if not is_marker(t)]


def node_regions(tokens: list[str]) -> dict[int, list[tuple[int, int]]]:
    """``nid -> [(start, end), ...]``: token index ranges (exclusive end, markers
    excluded) of every complete marked region. A node can occur more than once
    (``@sorted_agg`` repeats its argument). Regions cut by a statement split
    (``;`` inside a multi-statement rule) are ignored."""
    out: dict[int, list[tuple[int, int]]] = {}
    stack: list[tuple[int, int]] = []
    for i, t in enumerate(tokens):
        if not t or t[0] not in (_OPEN, _CLOSE):
            continue
        nid = int(t[1:])
        if t[0] == _OPEN:
            stack.append((nid, i))
        else:
            while stack and stack[-1][0] != nid:
                stack.pop()
            if stack:
                _, start = stack.pop()
                out.setdefault(nid, []).append((start + 1, i))
    return out


def splice(tokens: list[str], nid: int, new: Callable[[list[str]], list[str]]) -> list[str]:
    """Replace every occurrence of node ``nid`` by ``new(inner tokens)``.
    Markers inside replaced regions are kept only if ``new`` keeps them."""
    regions = sorted(node_regions(tokens).get(nid, []))
    if not regions:
        raise KeyError(nid)
    out: list[str] = []
    pos = 0
    for start, end in regions:
        if start - 1 < pos:      # nested in an earlier occurrence (cannot happen for one nid)
            continue
        out += tokens[pos:start - 1]
        out += [tokens[start - 1]] + new(tokens[start:end]) + [tokens[end]]
        pos = end + 1
    return out + tokens[pos:]


def render(tokens: list[str]) -> str:
    out: list[str] = []
    for t in tokens:
        if is_marker(t):
            continue
        if out and not (t in (",", ")", ".", "::", "]", "[") or out[-1] in ("(", ".", "::", "[")):
            out.append(" ")
        out.append(t)
    return "".join(out)


# ------------------------------------------------------------------ literals

_LITERALS: dict[str, list[str]] = {
    "int": ["0", "1", "2", "3", "7", "10", "16", "100", "(-1)", "(-42)", "500"],
    "bigint": ["0::bigint", "1::bigint", "(-1)::bigint", "10::bigint", "100::bigint", "1000::bigint"],
    "numeric": ["0.0::numeric", "0.5::numeric", "1.5::numeric", "2.25::numeric", "10.0::numeric",
                "42.5::numeric", "100.0::numeric"],
    "float8": ["0.0::float8", "0.5::float8", "1.0::float8", "(-0.0)::float8", "(-1.5)::float8",
               "10.0::float8", "100.0::float8", "5e-324::float8", "(1.0 / 3)::float8"],
    "text": ["''::text", "'a'::text", "'abc'::text", "'A'::text", "' '::text", "'%'::text",
             "'_'::text", "'x%'::text", "'ß'::text", "'é'::text", "'NaN'::text", "'0'::text",
             "'{\"k\": 1}'::text", "'[1,10)'::text", "'c4ca4238a0b923820dcc509a6f75849b'::text"],
    "bool": ["TRUE", "FALSE"],
    "date": ["'2024-02-29'::date", "'1970-01-01'::date", "'2000-01-01'::date",
             "'2024-01-01'::date", "'2024-12-31'::date", "'1999-12-31'::date"],
    "tstz": ["'2024-02-29 12:34:56+00'::timestamptz", "'epoch'::timestamptz",
             "'1999-12-31 23:59:59.999999+05:30'::timestamptz",
             "'2000-01-01 00:00:00+00'::timestamptz",
             "'2024-01-01 00:00:00+00'::timestamptz"],
    "interval": ["'1 day'::interval", "'-1 month'::interval", "'0'::interval",
                 "'1 year 2 mons 3 days 04:05:06.789'::interval",
                 "'00:00:00.000001'::interval", "'-3 hours'::interval", "'7 days'::interval"],
    "jsonb": ["'{}'::jsonb", "'{\"k\": 1, \"a\": [1, 2]}'::jsonb",
              "'{\"k\": 0, \"a\": [3, 4, 5]}'::jsonb",
              "'{\"k\": 2, \"a\": [0]}'::jsonb",
              "'{\"k\": -1, \"a\": [1, 2, 3]}'::jsonb"],
    "int4range": ["'empty'::int4range", "'[1,10)'::int4range", "'(,5]'::int4range", "'[3,)'::int4range",
                  "'[0,0]'::int4range", "'(,)'::int4range", "int4range(2, 40)"],
    "textarr": ["'{}'::text[]", "'{a,b}'::text[]", "'{NULL}'::text[]", "ARRAY['x'::text, NULL::text]",
                "'{a,b,c,d}'::text[]", "ARRAY['1'::text]"],
    "intarr": ["'{1,2,3}'::int[]", "'{}'::int[]", "'{NULL,1}'::int[]", "'{1,2,3,4}'::int[]",
               "ARRAY[1, 2, 3]", "ARRAY[1]"],
}

_FILL: dict[str, list[str]] = {
    "int": ["(x % 17)", "x", "(x % 3)", "(100 - x)"],
    "bigint": ["(x * 10)::bigint", "(x % 5)::bigint"],
    "numeric": ["round((x / 7.0)::numeric, 2)", "(x % 4)::numeric", "round((x / 3.0)::numeric, 2)"],
    "float8": ["(x / 3.0)::float8", "(x % 5)::float8"],
    "text": ["(x % 13)::text", "md5(x::text)", "repeat('ab', x % 4)", "chr(65 + x % 26)"],
    "bool": ["(x % 3 = 0)", "(x % 2 = 1)"],
    "date": ["('2024-01-01'::date + x)", "('2024-01-01'::date + x % 10)"],
    "tstz": ["('2024-01-01 00:00:00+00'::timestamptz + x * interval '1 hour')"],
    "interval": ["(x * interval '1 minute')", "make_interval(days => x % 40)"],
    "jsonb": ["jsonb_build_object('k', x % 10, 'a', jsonb_build_array(x, x % 3))"],
    "int4range": ["int4range(x, x + x % 10)", "int4range(x % 20, (x % 20) + 5)"],
    "textarr": ["ARRAY[x::text, (x % 3)::text]", "string_to_array((x % 100)::text, '')"],
    "intarr": ["ARRAY[x, x % 5]", "ARRAY[x % 3]"],
}


# ------------------------------------------------------------------ engine

Builtin_fn = Callable[["Engine", Ctx, dict, list[str], "Node | None"], tuple["Node | None", list[str]]]
BUILTINS: dict[str, Builtin_fn] = {}


def builtin(name: str):
    def deco(fn: Builtin_fn) -> Builtin_fn:
        BUILTINS[name] = fn
        return fn
    return deco


class Engine:
    def __init__(
        self,
        grammar: Grammar,
        schema: Schema,
        rng: random.Random,
        max_depth: int = 14,
        soft_depth: int = 8,
        max_steps: int = 6000,
        max_tries: int = 4,
        null_prob: float = 0.06,
    ) -> None:
        self.g, self.base_schema, self.rng = grammar, schema, rng
        self.max_depth, self.soft_depth, self.max_steps, self.max_tries = max_depth, soft_depth, max_steps, max_tries
        self.null_prob = null_prob
        self.alt_hits: Counter[int] = Counter()
        self.alt_boost: dict[int, float] = {}
        self._nid = 0
        missing = sorted({el.name for vs in grammar.rules.values() for v in vs for a in v.alts
                          for el in _walk(a.elems) if isinstance(el, Builtin) and el.name not in BUILTINS})
        if missing:
            raise ValueError(f"{grammar.source}: unknown builtins {missing}")
        self.new_testcase()

    # ---- per test case / statement state
    def new_testcase(self) -> None:
        self.schema = self.base_schema.copy()
        self.added: list[str] = []
        self.new_n = 0

    def _new_statement(self) -> None:
        self.steps = 0
        self.alias_n = 0
        self.cte_n = 0

    def statement(self, start: str | None = None, guide: Node | None = None) -> tuple[Node, list[str]]:
        """Generate one statement (possibly several, separated by ';' tokens)."""
        start = start or self.g.start
        for attempt in range(6):
            self._new_statement()
            n_added = len(self.added)
            try:
                node, toks = self.expand(start, None, Ctx(Scope()), guide if attempt < 2 else None)
            except Fail:
                for name in self.added[n_added:]:
                    self.schema.relations.pop(name, None)
                del self.added[n_added:]
                continue
            for uid in _uids(node):
                self.alt_hits[uid] += 1
            return node, toks
        raise Fail(f"could not derive {start!r}")

    def _mark(self, node: Node, toks: list[str]) -> list[str]:
        self._nid += 1
        node.nid = self._nid
        return [f"{_OPEN}{self._nid}"] + toks + [f"{_CLOSE}{self._nid}"]

    # ---- types
    def members(self, cls: str) -> list[str]:
        return self.g.class_members(cls)

    def pick_type(self, cls: str = "") -> str:
        ms = self.members(cls)
        if not ms:
            raise Fail(f"empty class {cls}")
        return self.rng.choices(ms, weights=[self.g.types[t].weight for t in ms])[0]

    def resolve_targ(self, ta: TypeArg | None, tv: dict, gtv: dict | None, guide: Node | None) -> str | None:
        if ta is None:
            return None
        if ta.kind == "param":
            return tv[ta.name]
        if ta.kind == "concrete":
            return ta.name
        if ta.kind == "local":
            if ta.name not in tv:
                t = (gtv or {}).get(ta.name)
                if t is None or (ta.cls and t not in self.members(ta.cls)):
                    t = self.pick_type(ta.cls)
                tv[ta.name] = t
            return tv[ta.name]
        cls = ta.name if ta.kind == "class" else ta.cls
        if guide is not None and guide.typ in self.members(cls):
            return guide.typ
        return self.pick_type(cls)

    def type_filter(self, arg: str, tv: dict) -> tuple[set[str], str | None]:
        """Allowed types for a builtin's type argument, and the local variable to
        bind to the chosen type (if the argument is an unbound variable)."""
        name, _, cls = arg.partition(":")
        if name == "*":
            return set(self.members(cls)), None
        if name in tv:
            return {tv[name]}, None
        if name in self.g.types:
            return {name}, None
        if name in self.g.classes:
            return set(self.g.classes[name]), None
        return set(self.members(cls)), name

    def bind_type(self, arg: str, tv: dict, guide_typ: str | None = None) -> str:
        allowed, var = self.type_filter(arg, tv)
        if guide_typ in allowed:
            t = guide_typ
        elif len(allowed) == 1:
            t = next(iter(allowed))
        else:
            ms = sorted(allowed)
            t = self.rng.choices(ms, weights=[self.g.types[m].weight for m in ms])[0]
        if var:
            tv[var] = t
        return t

    def sql_type(self, t: str) -> str:
        return self.g.types[t].sql

    # ---- names
    def alias(self) -> str:
        self.alias_n += 1
        return f"a{self.alias_n}"

    # ---- expansion
    def _order(self, cands: list[tuple[Variant, Alt, int]], depth: int, guide: Node | None) -> list[tuple[Variant, Alt, int]]:
        first = [c for c in cands if guide is not None and c[1].uid == guide.alt]
        rest = [c for c in cands if not first or c is not first[0]]
        lo = min(c[2] for c in cands)
        keyed = []
        for c in rest:
            w = c[1].weight * self.alt_boost.get(c[1].uid, 1.0)
            if depth >= self.soft_depth:
                w *= 0.15 ** (c[2] - lo)
            if w <= 0:
                continue
            keyed.append((self.rng.random() ** (1.0 / w), c))
        keyed.sort(key=lambda kc: -kc[0])
        return first + [c for _, c in keyed]

    def _allowed(self, alt: Alt, flags: frozenset[str]) -> bool:
        return not (alt.require - flags) and not (alt.forbid & flags)

    def expand(self, name: str, typ: str | None, ctx: Ctx, guide: Node | None = None) -> tuple[Node, list[str]]:
        self.steps += 1
        if self.steps > self.max_steps:
            raise Fail("step budget")
        if guide is not None and (guide.sym != name or guide.typ != typ):
            guide = None
        cands = []
        for v, a in self.g.candidates(name, typ):
            md = a.mind.get(typ, INF)
            if self._allowed(a, ctx.flags) and ctx.depth + md <= self.max_depth:
                cands.append((v, a, md))
        if not cands:
            raise Fail(f"no alternative for {name}<{typ}>")
        for v, a, _ in self._order(cands, ctx.depth, guide)[: self.max_tries]:
            snap = ctx.scope.snapshot()
            n_added, counters = len(self.added), (self.alias_n, self.cte_n, self.new_n)
            try:
                node, toks = self._alt(name, v, a, typ, ctx, guide if guide is not None and guide.alt == a.uid else None)
                return node, self._mark(node, toks)
            except Fail:
                ctx.scope.restore(snap)
                self.alias_n, self.cte_n, self.new_n = counters
                for rel in self.added[n_added:]:
                    self.schema.relations.pop(rel, None)
                del self.added[n_added:]
        raise Fail(f"{name}<{typ}> exhausted")

    def _alt(self, name: str, v: Variant, a: Alt, typ: str | None, ctx: Ctx, guide: Node | None) -> tuple[Node, list[str]]:
        attrs = self.g.attrs.get(name, {})
        scope, flags, shape = ctx.scope, ctx.flags, ctx.shape
        frame = (scope, len(scope.items)) if "frame" in attrs else ctx.frame
        if "scope" in attrs:
            mode = (attrs["scope"] or ["correlated"])[0]
            isolated = mode == "isolated" or "in_agg" in ctx.flags or ctx.frame is not None
            scope = Scope(parent=scope, col_parent=None if isolated else scope)
            flags = frozenset()
            frame = None
        if "set" in attrs:
            flags = flags | frozenset(attrs["set"])
        if "clear" in attrs:
            flags = flags - frozenset(attrs["clear"])
        tv: dict[str, str] = {v.param: typ} if v.param and typ else {}
        gtv = guide.tv if guide is not None else None
        val = None
        if "shape" in attrs:
            shape = val = self._shape(attrs["shape"], tv, guide.val if guide is not None else None)
        ctx2 = Ctx(scope, flags, shape, frame, ctx.depth + 1)
        kids, toks = self._elems(a, ctx2, tv, gtv, guide.kids if guide is not None else None)
        locals_ = {k: t for k, t in tv.items() if k != v.param}
        return Node(name, typ, a.uid, kids, val, locals_ or None), toks

    def _shape(self, args: list[str], tv: dict, guided: Any) -> tuple[str, ...]:
        if args:
            return tuple(self.bind_type(x, tv) for x in args)
        if isinstance(guided, tuple) and guided and all(t in self.g.types for t in guided):
            return guided
        cls = "shape" if "shape" in self.g.classes else ""
        return tuple(self.pick_type(cls) for _ in range(self.rng.choice((1, 1, 2, 2, 3))))

    def _elems(self, a: Alt, ctx: Ctx, tv: dict, gtv: dict | None, gkids: list | None) -> tuple[list, list[str]]:
        n = len(a.elems)
        kids: list = [None] * n
        parts: list[list[str]] = [[] for _ in range(n)]
        for i in sorted(range(n), key=lambda i: (i not in a.early, i)):
            g = gkids[i] if gkids is not None and i < len(gkids) else None
            kids[i], parts[i] = self._el(a.elems[i], ctx, tv, gtv, g)
        return kids, [t for p in parts for t in p]

    def _el(self, el: object, ctx: Ctx, tv: dict, gtv: dict | None, guide: Node | None) -> tuple[Node | None, list[str]]:
        if isinstance(el, Lit):
            return None, [el.text]
        if isinstance(el, NT):
            t = self.resolve_targ(el.targ, tv, gtv, guide)
            return self.expand(el.name, t, ctx, guide)
        if isinstance(el, Builtin):
            if guide is not None and guide.sym != "@" + el.name:
                guide = None
            node, toks = BUILTINS[el.name](self, ctx, tv, el.args, guide)
            return node, (self._mark(node, toks) if node is not None and toks else toks)
        if isinstance(el, TypeName):
            if el.var not in tv:
                tv[el.var] = (gtv or {}).get(el.var) or self.pick_type()
            return None, [self.sql_type(tv[el.var])]
        if isinstance(el, Group):
            return self._group(el, ctx, tv, gtv, guide if guide is not None and guide.sym == "#grp" else None)
        if isinstance(el, Repeat):
            return self._repeat(el, ctx, tv, gtv, guide if guide is not None and guide.sym == "#rep" else None)
        raise TypeError(el)

    def _group(self, el: Group, ctx: Ctx, tv: dict, gtv: dict | None, guide: Node | None) -> tuple[Node, list[str]]:
        alts = [a for a in el.alts if self._allowed(a, ctx.flags)]
        cands = [(None, a, 0) for a in alts]
        if not cands:
            raise Fail("no group alternative")
        for _, a, _ in self._order(cands, 0, guide)[: self.max_tries]:  # type: ignore[arg-type]
            snap = ctx.scope.snapshot()
            counters = (self.alias_n, self.cte_n, self.new_n)
            try:
                kids, toks = self._elems(a, ctx, tv, gtv, guide.kids if guide is not None and guide.alt == a.uid else None)
                return Node("#grp", None, a.uid, kids), toks
            except Fail:
                ctx.scope.restore(snap)
                self.alias_n, self.cte_n, self.new_n = counters
        raise Fail("group exhausted")

    def _repeat(self, el: Repeat, ctx: Ctx, tv: dict, gtv: dict | None, guide: Node | None) -> tuple[Node, list[str]]:
        if guide is not None:
            n = max(el.lo, min(el.hi, len(guide.kids)))
        elif el.lo == 0 and el.hi == 1:
            n = int(self.rng.random() < (0.5 if el.p is None else el.p))
        else:
            n = el.lo + int(min(el.hi - el.lo, self.rng.expovariate(0.8)))
        if ctx.depth >= self.max_depth - 1:
            n = el.lo
        kids: list = []
        toks: list[str] = []
        for i in range(n):
            g = guide.kids[i] if guide is not None and i < len(guide.kids) else None
            snap = ctx.scope.snapshot()
            counters = (self.alias_n, self.cte_n, self.new_n)
            try:
                k, t = self._el(el.elem, ctx, tv, gtv, g)
            except Fail:
                if i < el.lo:
                    raise
                ctx.scope.restore(snap)
                self.alias_n, self.cte_n, self.new_n = counters
                break
            if toks and el.sep:
                toks.append(el.sep)
            kids.append(k)
            toks += t
        return Node("#rep", None, 0, kids), toks

    # ---- column visibility
    def visible(self, ctx: Ctx, local_only: bool = False) -> list[tuple[Scope, Item, Column]]:
        out = []
        s: Scope | None = ctx.scope
        in_agg = "in_agg" in ctx.flags
        while s is not None:
            items = s.items
            if ctx.frame is not None and ctx.frame[0] is s:
                items = items[ctx.frame[1]:]
            restrict = s.grouped and not (s is ctx.scope and in_agg)
            for it in items:
                if it.hidden:
                    continue
                for c in it.columns:
                    if restrict and (it.alias, c.name) not in s.group_cols:
                        continue
                    out.append((s, it, c))
            if local_only or in_agg:
                break
            s = s.col_parent
        return out

    def relations(self, ctx: Ctx) -> list[Relation]:
        rels: list[Relation] = []
        s: Scope | None = ctx.scope
        while s is not None:
            rels += s.rels
            s = s.parent
        return rels + list(self.schema.relations.values())

    def literal(self, t: str, allow_null: bool = False) -> str:
        if allow_null and self.rng.random() < self.null_prob:
            return f"NULL::{self.sql_type(t)}"
        vals = _LITERALS.get(t)
        if not vals:
            return f"NULL::{self.sql_type(t)}"
        if t == "int" and self.rng.random() < 0.3:
            v = self.rng.randint(-20, 60)
            return str(v) if v >= 0 else f"({v})"
        return self.rng.choice(vals)

    def fill_expr(self, c: Column) -> str:
        t = c.type
        if "pk" in c.flags:
            return {"int": "x", "bigint": "x::bigint", "numeric": "x::numeric", "text": "x::text"}.get(t, f"x::{self.sql_type(t)}")
        exprs = _FILL.get(t) or [self.literal(t)]
        return self.rng.choice(exprs)

    def stats(self) -> dict[str, Any]:
        all_alts = {a.uid for vs in self.g.rules.values() for v in vs for a in v.alts}
        hit = sum(1 for u in all_alts if self.alt_hits[u])
        return {"alternatives": len(all_alts), "alternatives_used": hit}


def _walk(elems):
    for el in elems:
        yield el
        if isinstance(el, Repeat):
            yield from _walk([el.elem])
        elif isinstance(el, Group):
            for a in el.alts:
                yield from _walk(a.elems)


def _uids(node: Node):
    for _, n in node.walk():
        if n.sym[0] not in "#@":
            yield n.alt


# ------------------------------------------------------------------ builtins

def _flag_args(args: list[str]) -> tuple[list[str], set[str]]:
    words = {"plain", "writable", "base", "pk", "nopk", "distinct", "shape", "values", "select", "local", "nobind",
             "nowin", "rollup", "cube", "sets", "table", "view", "matview", "partitioned", "generated", "notnull",
             "identity", "one"}
    return [a for a in args if a not in words], {a for a in args if a in words}


@builtin("lit")
def _b_lit(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    t = eng.bind_type(args[0] if args else "*", tv, guide.typ if guide is not None else None)
    if guide is not None and guide.typ == t and isinstance(guide.val, str):
        v = guide.val
    else:
        v = eng.literal(t)
    return Node("@lit", t, val=v), [v]


@builtin("col")
def _b_col(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    targs, fl = _flag_args(args)
    allowed, var = eng.type_filter(targs[0] if targs else "*", tv)
    cands = [(s, it, c) for s, it, c in eng.visible(ctx, local_only="local" in fl) if c.type in allowed]
    if not cands:
        raise Fail("no column")
    pick = None
    if guide is not None and isinstance(guide.val, tuple) and len(guide.val) == 3:
        alias, rel, col = guide.val
        same = [x for x in cands if (x[1].rel, x[2].name) == (rel, col)]
        pick = next((x for x in same if x[1].alias == alias), same[0] if same else None)
    if pick is None:
        weights = [3.0 if s is ctx.scope else 1.0 for s, _, _ in cands]
        pick = eng.rng.choices(cands, weights=weights)[0]
    _, it, c = pick
    if var:
        tv[var] = c.type
    return Node("@col", c.type, val=(it.alias, it.rel, c.name)), [it.alias, ".", c.name]


def _pick_rel(eng: Engine, ctx: Ctx, fl: set[str], guide: Node | None, names: list[str] | None = None) -> Relation:
    rels = eng.relations(ctx)
    if names:
        rels = [r for r in rels if r.name in names]
    if "writable" in fl or "base" in fl:
        rels = [r for r in rels if r.writable]
    if "plain" in fl:
        rels = [r for r in rels if r.kind == "table"]
    if "nopk" in fl:
        rels = [r for r in rels if not any("pk" in c.flags for c in r.columns)]
    if not rels:
        raise Fail("no relation")
    if guide is not None:
        for r in rels:
            if r.name == guide.val:
                return r
    return eng.rng.choices(rels, weights=[3.0 if r.kind == "cte" else 1.0 for r in rels])[0]


@builtin("table")
def _b_table(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    names, fl = _flag_args(args)
    rel = _pick_rel(eng, ctx, fl, guide, names)
    if "plain" in fl:
        ctx.scope.items.append(Item(rel.name, rel.name, list(rel.columns)))
        return Node("@table", val=rel.name), [rel.name]
    a = eng.alias()
    ctx.scope.items.append(Item(a, rel.name, list(rel.columns)))
    return Node("@table", val=rel.name), [rel.name, "AS", a]


@builtin("target")
def _b_target(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    names, fl = _flag_args(args)
    rel = _pick_rel(eng, ctx, fl | {"writable"}, guide, names)
    a = rel.name if "plain" in fl else eng.alias()
    it = Item(a, rel.name, list(rel.columns), hidden="nobind" in fl)
    ctx.scope.items.append(it)
    ctx.scope.target = it
    return Node("@target", val=rel.name), [rel.name] if "plain" in fl else [rel.name, "AS", a]


@builtin("target_col")
def _b_target_col(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    targs, fl = _flag_args(args)
    it = ctx.scope.target or (ctx.scope.items[-1] if ctx.scope.items else None)
    if it is None:
        raise Fail("no target")
    allowed, var = eng.type_filter(targs[0] if targs else "*", tv)
    cols = [c for c in it.columns if c.type in allowed
            and "generated" not in c.flags
            and ("writable" not in fl or c.writable)
            and ("distinct" not in fl or c.name not in ctx.scope.used_cols)
            and ("pk" not in fl or "pk" in c.flags)]
    if not cols:
        raise Fail("no target column")
    c = next((c for c in cols if guide is not None and c.name == guide.val), None) or eng.rng.choice(cols)
    if var:
        tv[var] = c.type
    if "distinct" in fl:
        ctx.scope.used_cols.add(c.name)
    return Node("@target_col", c.type, val=c.name), [c.name]


@builtin("items")
def _b_items(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    rules, fl = _flag_args(args)
    rule = rules[0] if rules else "select_item"
    if ctx.shape is not None:
        types = list(ctx.shape)
    elif guide is not None and isinstance(guide.val, tuple) and all(t in eng.g.types for t in guide.val):
        types = list(guide.val)
    else:
        cls = "shape" if "shape" in eng.g.classes else ""
        types = [eng.pick_type(cls) for _ in range(eng.rng.choice((1, 2, 2, 3, 4)))]
    flags = (ctx.flags | ({"win_ok"} if "nowin" not in fl else set())
             | ({"agg_ok"} if ctx.scope.grouped else set()))
    ctx2 = replace(ctx, flags=frozenset(flags), shape=None)
    kids, toks = [], []
    for i, t in enumerate(types):
        g = guide.kids[i] if guide is not None and i < len(guide.kids) else None
        k, tk = eng.expand(rule, t, ctx2, g)
        if toks:
            toks.append(",")
        toks += tk + ["AS", f"c{i}"]
        kids.append(k)
    ctx.scope.out = types
    return Node("@items", val=tuple(types), kids=kids), toks


@builtin("ordinal")
def _b_ordinal(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    out = ctx.scope.out
    if not out:
        raise Fail("no select list")
    if args and args[0] not in ("*",):
        allowed, _ = eng.type_filter(args[0], tv)
        idx = [i for i, t in enumerate(out) if t in allowed]
    else:
        idx = list(range(len(out)))
    if not idx:
        raise Fail("no ordinal")
    i = guide.val if guide is not None and guide.val in idx else eng.rng.choice(idx)
    return Node("@ordinal", val=i), [str(i + 1)]


@builtin("derived_alias")
def _b_derived_alias(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    if not ctx.shape:
        raise Fail("no shape")
    a = eng.alias()
    ctx.scope.items.append(Item(a, "derived", [Column(f"c{i}", t) for i, t in enumerate(ctx.shape)]))
    return Node("@derived_alias"), [a]


@builtin("cte_name")
def _b_cte_name(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    if not ctx.shape:
        raise Fail("no shape")
    eng.cte_n += 1
    name = f"cte{eng.cte_n}"
    ctx.scope.rels.append(Relation(name, [Column(f"c{i}", t) for i, t in enumerate(ctx.shape)], "cte"))
    return Node("@cte_name"), [name]


@builtin("define_rel")
def _b_define_rel(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    """``@define_rel(name, type, ...)``: make a relation with columns c0.. visible
    (recursive CTEs, whose name is used inside their own definition)."""
    name, *types = args
    ctx.scope.rels.append(Relation(name, [Column(f"c{i}", eng.bind_type(t, tv)) for i, t in enumerate(types)], "cte"))
    return None, []


@builtin("define_alias")
def _b_define_alias(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    nolist = bool(args) and args[0] == "-"
    types = [eng.bind_type(t, tv) for t in (args[1:] if nolist else args)]
    a = eng.alias()
    ctx.scope.items.append(Item(a, "srf", [Column(f"c{i}", t) for i, t in enumerate(types)]))
    if nolist:
        return Node("@define_alias"), [a]
    toks = [a, "("]
    for i in range(len(types)):
        toks += ([","] if i else []) + [f"c{i}"]
    return Node("@define_alias"), toks + [")"]


@builtin("group_keys")
def _b_group_keys(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    mode = args[0] if args else "plain"
    cands = [(it, c) for _, it, c in eng.visible(ctx, local_only=True)]
    if not cands:
        raise Fail("nothing to group by")
    k = min(len(cands), eng.rng.choice((1, 1, 2, 2, 3)))
    picked = eng.rng.sample(cands, k)
    if guide is not None and isinstance(guide.val, list):
        again = []
        for alias, rel, col in map(tuple, guide.val):
            same = [(it, c) for it, c in cands if (it.rel, c.name) == (rel, col) and (it, c) not in again]
            hit = next((x for x in same if x[0].alias == alias), same[0] if same else None)
            if hit:
                again.append(hit)
        if again:
            picked = again
    refs = [[it.alias, ".", c.name] for it, c in picked]
    flat: list[str] = []
    if mode == "sets":
        flat += ["GROUPING", "SETS", "("]
        for i, r in enumerate(refs):
            flat += ([","] if i else []) + ["("] + r + [")"]
        flat += [",", "(", ")", ")"]
    else:
        for i, r in enumerate(refs):
            flat += ([","] if i else []) + r
        if mode in ("rollup", "cube"):
            flat = [mode.upper(), "("] + flat + [")"]
    ctx.scope.grouped = True
    ctx.scope.group_cols = {(it.alias, c.name) for it, c in picked}
    return Node("@group_keys", val=[(it.alias, it.rel, c.name) for it, c in picked]), flat


@builtin("global_agg")
def _b_global_agg(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    ctx.scope.grouped = True
    ctx.scope.group_cols = set()
    return None, []


@builtin("new_table")
def _b_new_table(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    _, fl = _flag_args(args)
    kind = next((k for k in ("view", "matview", "partitioned") if k in fl), "table")
    eng.new_n += 1
    name = f"n{eng.new_n}"
    cols = [Column(f"c{i}", t) for i, t in enumerate(ctx.shape or ())] if "shape" in fl else []
    rel = Relation(name, cols, kind)
    eng.schema.add(rel)
    eng.added.append(name)
    ctx.scope.newrel = rel
    ctx.scope.target = Item(name, name, rel.columns)
    return Node("@new_table"), [name]


@builtin("new_col")
def _b_new_col(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    targs, fl = _flag_args(args)
    rel = ctx.scope.newrel
    if rel is None:
        raise Fail("no new table")
    t = eng.bind_type(targs[0] if targs else "*", tv, guide.typ if guide is not None else None)
    c = Column(f"c{len(rel.columns)}", t, frozenset(fl & {"generated", "pk", "notnull", "identity"}))
    rel.columns.append(c)
    return Node("@new_col", t), [c.name, eng.sql_type(t)]


@builtin("newrel_col")
def _b_newrel_col(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    rel = ctx.scope.newrel
    if rel is None:
        raise Fail("no new table")
    allowed, var = eng.type_filter(args[0] if args else "*", tv)
    cols = [c for c in rel.columns if c.type in allowed and "generated" not in c.flags]
    if not cols:
        raise Fail("no column")
    c = eng.rng.choice(cols)
    if var:
        tv[var] = c.type
    return Node("@newrel_col", c.type, val=c.name), [c.name]


@builtin("fill")
def _b_fill(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    """``INSERT INTO <new table> SELECT ... FROM generate_series(1, n) AS g(x)``."""
    rel = ctx.scope.newrel or (eng.schema.relations.get(eng.added[-1]) if eng.added else None)
    if rel is None or not rel.writable:
        raise Fail("nothing to fill")
    cols = [c for c in rel.columns if c.writable]
    if not cols:
        raise Fail("no writable column")
    head = f"INSERT INTO {rel.name} ({', '.join(c.name for c in cols)}) SELECT "
    sig = (rel.name, tuple((c.name, c.type, c.flags) for c in cols))
    if guide is not None and isinstance(guide.val, tuple) and len(guide.val) == 2 and guide.val[0] == sig:
        sql = guide.val[1]
    else:
        n = int(args[0]) if args and args[0].isdigit() else eng.rng.choice((5, 20, 100))
        exprs = ", ".join(eng.fill_expr(c) for c in cols)
        sql = f"{head}{exprs} FROM generate_series(1, {n}) AS g(x)"
    return Node("@fill", val=(sig, sql)), [sql]


def _wrap_col_expr(eng: Engine, it: Item, c: Column, tk: list[str]) -> list[str]:
    out = tk
    if it.rel == "t1" and c.name == "c1":
        return ["NULLIF", "(", "NULL::int", ","] + out + [")"]
    if c.type == "numeric":
        out = ["(", "ABS", "("] + out + [")", "%", "1000", ")"]
    if c.flags & {"pk", "notnull"} or c.name == "c0":
        fallback = _LITERALS.get(c.type, [f"NULL::{eng.sql_type(c.type)}"])[0]
        out = ["COALESCE", "("] + out + [",", fallback, ")"]
    return out


@builtin("insert_body")
def _b_insert_body(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    _, fl = _flag_args(args)
    it = ctx.scope.target
    if it is None:
        raise Fail("no target")
    writable = [c for c in it.columns if c.writable]
    if not writable:
        raise Fail("nothing insertable")
    by_name = {c.name: c for c in writable}
    must = [c for c in writable if c.flags & {"pk", "notnull"}]
    gval = guide.val if guide is not None and isinstance(guide.val, tuple) and len(guide.val) == 3 else None
    if gval and gval[0] and all(n in by_name for n in gval[0]) and all(c.name in gval[0] for c in must):
        cols = [by_name[n] for n in gval[0]]
    else:
        rest = [c for c in writable if c not in must]
        cols = must + [c for c in rest if eng.rng.random() < 0.7]
        if not cols:
            cols = [eng.rng.choice(writable)]
        cols.sort(key=lambda c: it.columns.index(c))
        gval = None
    has_constraints = any(c.flags & {"pk", "notnull"} or c.type == "numeric" for c in cols) or it.rel == "tp"
    has_pk = any("pk" in c.flags for c in it.columns)
    use_values = True if ("values" in fl or has_constraints) else (gval[1] if gval else ("select" not in fl and eng.rng.random() < 0.6))
    gk = guide.kids if gval and guide is not None else []
    toks = ["("] + [t for i, c in enumerate(cols) for t in ([","] if i else []) + [c.name]] + [")"]
    was_hidden, it.hidden = it.hidden, True
    try:
        kids: list = []
        if use_values:
            nrows = 1 if ("one" in fl or has_pk) else (gval[2] if gval and gval[2] >= 1 else eng.rng.choice((1, 1, 2, 3)))
            toks.append("VALUES")
            for r in range(nrows):
                toks += ([","] if r else []) + ["("]
                for i, c in enumerate(cols):
                    j = len(kids)
                    k, tk = eng.expand("insert_value", c.type, ctx, gk[j] if j < len(gk) else None)
                    tk = _wrap_col_expr(eng, it, c, tk)
                    toks += ([","] if i else []) + tk
                    kids.append(k)
                toks.append(")")
        else:
            nrows = 0
            k, tk = eng.expand("insert_query", None, replace(ctx, shape=tuple(c.type for c in cols)),
                               gk[0] if gk else None)
            kids = [k]
            toks += tk
    finally:
        it.hidden = was_hidden
    return Node("@insert_body", kids=kids, val=(tuple(c.name for c in cols), use_values, nrows)), toks


@builtin("out")
def _b_out(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    """Declare the current shape as this level's output (ORDER BY ordinals of set queries)."""
    if not ctx.shape:
        raise Fail("no shape")
    ctx.scope.out = list(ctx.shape)
    return None, []


@builtin("shape_list")
def _b_shape_list(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    """Comma-separated ``rule<T>`` for every type of the current shape (VALUES rows)."""
    if not ctx.shape:
        raise Fail("no shape")
    rule = args[0] if args else "expr"
    ctx2 = replace(ctx, shape=None)
    kids, toks = [], []
    for i, t in enumerate(ctx.shape):
        g = guide.kids[i] if guide is not None and i < len(guide.kids) else None
        k, tk = eng.expand(rule, t, ctx2, g)
        toks += ([","] if i else []) + tk
        kids.append(k)
    return Node("@shape_list", kids=kids), toks


@builtin("sorted_agg")
def _b_sorted_agg(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    """``@sorted_agg(FUNC, T, extra...)`` -> ``FUNC(e, extra ORDER BY e)``: order-sensitive
    aggregates ordered by their own argument, so the result is plan-independent."""
    func, targ, *extra = args
    t = eng.bind_type(targ, tv, guide.typ if guide is not None else None)
    g = guide.kids[0] if guide is not None and guide.kids else None
    k, tk = eng.expand("expr", t, ctx, g)
    desc = guide.val if guide is not None and isinstance(guide.val, bool) else eng.rng.random() < 0.3
    toks = [func, "("] + tk + [x for e in extra for x in (",", e)] + ["ORDER", "BY"] + tk + (["DESC"] if desc else []) + [")"]
    return Node("@sorted_agg", t, kids=[k], val=desc), toks


@builtin("join_eq")
def _b_join_eq(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    """Equality between a column of the right-most join input and a column of the
    same type from an earlier input of the same join (hash/merge-joinable)."""
    if ctx.frame is None:
        raise Fail("not in a join")
    scope, start = ctx.frame
    items = [it for it in scope.items[start:] if not it.hidden]
    if len(items) < 2:
        raise Fail("one-sided join")
    right, lefts = items[-1], [items[0]]
    keyable = set(eng.members("key")) if "key" in eng.g.classes else set(eng.g.types)
    pairs = [(l, lc, rc) for l in lefts for lc in l.columns for rc in right.columns
             if lc.type == rc.type and lc.type in keyable]
    if not pairs:
        raise Fail("no equi-join pair")
    again = [p for p in pairs if guide is not None and (p[0].rel, p[1].name, right.rel, p[2].name) == guide.val]
    same_name = [p for p in pairs if p[1].name == p[2].name]
    l, lc, rc = (again or [None])[0] or eng.rng.choice(same_name if same_name and eng.rng.random() < 0.6 else pairs)
    return (Node("@join_eq", val=(l.rel, lc.name, right.rel, rc.name)),
            ["(", l.alias, ".", lc.name, "=", right.alias, ".", rc.name, ")"])


@builtin("target_name")
def _b_target_name(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    it = ctx.scope.target
    if it is None:
        raise Fail("no target")
    return None, [it.rel]


@builtin("fresh_name")
def _b_fresh_name(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    eng.new_n += 1
    return None, [f"{args[0] if args else 'x'}{eng.new_n}"]


@builtin("assign")
def _b_assign(eng: Engine, ctx: Ctx, tv: dict, args: list[str], guide: Node | None):
    it = ctx.scope.target
    if it is None:
        raise Fail("no target")
    cols = [c for c in it.columns if c.writable and "pk" not in c.flags]
    if not cols:
        cols = [c for c in it.columns if c.writable]
    if not cols:
        raise Fail("nothing updatable")
    by_name = {c.name: c for c in cols}
    if guide is not None and isinstance(guide.val, list) and guide.val and all(n in by_name for n in guide.val):
        picked = [by_name[n] for n in guide.val]
    else:
        picked = eng.rng.sample(cols, min(len(cols), eng.rng.choice((1, 1, 2))))
    toks, kids = [], []
    for i, c in enumerate(picked):
        g = guide.kids[i] if guide is not None and i < len(guide.kids) else None
        k, tk = eng.expand("assign_value", c.type, ctx, g)
        tk = _wrap_col_expr(eng, it, c, tk)
        toks += ([","] if i else []) + [c.name, "="] + tk
        kids.append(k)
    return Node("@assign", kids=kids, val=[c.name for c in picked]), toks
