"""Metamorphic follow-up queries built on the derivation tree.

A metamorphic oracle runs a query and a transformed query whose results must be
related in a known way, and reports a violation as a wrong result. Tools such as
SQLancer build the transformed query from strings they generated themselves;
here it is built from the *typed derivation tree*: every node knows its grammar
symbol, its SQL type and (through the engine's span markers) exactly which
tokens it produced. A rewrite therefore edits one typed node and keeps the
statement well-typed and well-scoped, so follow-ups are almost never rejected
by the parser or analyser.

Checks produced for one query statement (``Check.lhs`` is ``None`` when the
left side is the statement itself):

``tlp_where``      Ternary Logic Partitioning (Rigger and Su, OOPSLA 2020) on a
                   ``WHERE p``: a SELECT without its WHERE clause equals the
                   multiset union of the SELECT under ``p``, ``NOT p`` and
                   ``p IS NULL``. With DISTINCT the arms are combined with UNION.
                   The SELECT can be the query itself or any SELECT whose result is
                   consumed as a multiset (derived table, CTE body, set-operation
                   arm, IN / EXISTS / LATERAL subquery); then both sides are the
                   whole statement, one with the WHERE dropped and one with that
                   SELECT replaced by its partitioned form.
``tlp_having``     The same partitioning on the ``HAVING`` clause of a grouped SELECT.
``norec``          Non-optimizing reference engine construction (Rigger and Su,
                   ESEC/FSE 2020): ``SELECT count(*) FROM .. WHERE p`` equals
                   ``SELECT sum(CASE WHEN p THEN 1 ELSE 0 END) FROM ..``, where the
                   predicate cannot be used to plan the scan.
``expr:<name>``    Equivalent-expression rewrite of one typed ``expr<T>`` node
                   (in the spirit of EET, Jiang and Su, OSDI 2024), e.g.
                   ``e -> COALESCE(e, e)``, ``e -> (SELECT e)``, ``p -> NOT NOT p``;
                   the whole query result must not change.
``cte_materialize`` Toggle ``MATERIALIZED`` / ``NOT MATERIALIZED`` on a CTE.
``table_fence``    Replace one base-table reference ``t AS a`` with
                   ``(SELECT * FROM t OFFSET 0) AS a``: the planner can no longer
                   push predicates into, reorder, or eliminate that scan (index
                   choice, join removal, self-join elimination, partition pruning).

False-positive control lives in three places: only queries that are
deterministic (:func:`pgfuzz.eval.differential.eligible`) get checks;
partition-based checks that de-duplicate or group rows are only built when the
values involved have a unique text form (``1.0 = 1.00`` and ``'1 day' =
'24 hours'`` would otherwise let two correct plans print different
representatives); and the executor re-runs both sides before a mismatch counts.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any, Callable

from pgfuzz.eval.differential import eligible, masks_floats
from pgfuzz.grammar.dsl import Builtin, Grammar
from pgfuzz.grammar.engine import Node, node_regions, render
from pgfuzz.grammar.schema import Schema

# Types whose equality implies an identical text form (so DISTINCT / GROUP BY
# may pick any representative of a group without changing the output).
UNIQUE_TEXT_TYPES = frozenset({"int", "bigint", "text", "bool", "date", "tstz", "int4range", "intarr", "textarr"})

KINDS = ("tlp_where", "tlp_having", "norec", "expr", "cte_materialize", "table_fence")
# Partitioning checks apply to fewer queries, so they get the larger weights.
DEFAULT_WEIGHTS = {"tlp_where": 6.0, "tlp_having": 5.0, "norec": 3.0, "expr": 3.0,
                   "cte_materialize": 1.5, "table_fence": 1.5}


@dataclass
class Check:
    stmt: int                 # index of the statement in the test case
    kind: str                 # e.g. "tlp_where", "expr:scalar_sub"
    lhs: str | None           # None: the statement itself
    rhs: str
    mask: bool = False        # mask float columns when digesting both sides

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------ tree index

class _Tree:
    """Navigation over one statement: nodes by nid, parents, token regions."""

    def __init__(self, tree: Node, toks: list[str], alts: dict[int, Any]) -> None:
        self.tree, self.toks, self.alts = tree, toks, alts
        self.regions = node_regions(toks)
        self.parent: dict[int, Node | None] = {}
        self.nodes: list[Node] = []
        self._index(tree, None)

    def _index(self, n: Node, parent: Node | None) -> None:
        self.parent[id(n)] = parent
        self.nodes.append(n)
        for k in n.kids:
            if k is not None:
                self._index(k, n)

    def region(self, n: Node) -> tuple[int, int] | None:
        occ = self.regions.get(n.nid)
        return occ[0] if occ and len(occ) == 1 else None

    def tokens(self, n: Node) -> list[str] | None:
        r = self.region(n)
        return self.toks[r[0]:r[1]] if r else None

    def ancestors(self, n: Node):
        p = self.parent.get(id(n))
        while p is not None:
            yield p
            p = self.parent.get(id(p))

    def child(self, n: Node, sym: str) -> Node | None:
        """Direct child with this symbol, looking through ``?``/``*`` and groups."""
        for k in n.kids:
            if k is None:
                continue
            if k.sym == sym:
                return k
            if k.sym in ("#rep", "#grp"):
                hit = self.child(k, sym)
                if hit is not None:
                    return hit
        return None

    def contains(self, n: Node, syms: set[str]) -> bool:
        return any(m.sym in syms for _, m in n.walk())

    def alt_builtins(self, n: Node) -> set[str]:
        a = self.alts.get(n.alt)
        return {el.name for el in (a.elems if a else []) if isinstance(el, Builtin)}

    def replace(self, n: Node, new: list[str]) -> list[str]:
        """Statement tokens with node ``n`` replaced by ``new``."""
        start, end = self.region(n)  # type: ignore[misc]
        return self.toks[:start] + new + self.toks[end:]


def _paren(t: list[str]) -> list[str]:
    return ["("] + t + [")"]


# ------------------------------------------------------------------ expression rewrites
#
# Each rewrite maps the tokens of an expr<T> to an expression of the same type
# and the same value for every input, NULL and errors included.

ExprRewrite = Callable[[list[str]], list[str]]

_ANY: dict[str, ExprRewrite] = {
    "case_true": lambda e: ["CASE", "WHEN", "TRUE", "THEN"] + _paren(e) + ["END"],
    "coalesce_self": lambda e: ["COALESCE", "("] + _paren(e) + [","] + _paren(e) + [")"],
    "scalar_sub": lambda e: ["(", "SELECT"] + _paren(e) + [")"],
}
_BY_TYPE: dict[str, dict[str, ExprRewrite]] = {
    "int": {"plus_zero": lambda e: ["("] + _paren(e) + ["+", "0", ")"],
            "times_one": lambda e: ["("] + _paren(e) + ["*", "1", ")"]},
    "bigint": {"plus_zero": lambda e: ["("] + _paren(e) + ["+", "0", ")"]},
    "numeric": {"plus_zero": lambda e: ["("] + _paren(e) + ["+", "0", ")"],
                "times_one": lambda e: ["("] + _paren(e) + ["*", "1", ")"]},
    "float8": {"times_one": lambda e: ["("] + _paren(e) + ["*", "1", ")"]},   # -0.0 + 0 would print 0
    "text": {"concat_empty": lambda e: ["("] + _paren(e) + ["||", "''::text", ")"]},
    "date": {"plus_zero": lambda e: ["("] + _paren(e) + ["+", "0", ")"]},
    "bool": {"double_not": lambda e: ["(", "NOT", "(", "NOT"] + _paren(e) + [")", ")"],
             "and_true": lambda e: ["("] + _paren(e) + ["AND", "TRUE", ")"],
             "or_false": lambda e: ["("] + _paren(e) + ["OR", "FALSE", ")"],
             "case_bool": lambda e: ["CASE", "WHEN"] + _paren(e) + ["THEN", "TRUE", "WHEN", "NOT"]
                                    + _paren(e) + ["THEN", "FALSE", "END"]},
}


def expr_rewrites(typ: str | None) -> dict[str, ExprRewrite]:
    return {**_ANY, **_BY_TYPE.get(typ or "", {})}


# ------------------------------------------------------------------ the rewriter

class Rewriter:
    """Builds metamorphic checks for query statements of grammar test cases."""

    def __init__(self, grammar: Grammar, rng: random.Random, per_query: int = 1,
                 weights: dict[str, float] | None = None, query_rules: tuple[str, ...] = ("query",)) -> None:
        self.rng = rng
        self.per_query = per_query
        self.weights = {k: float(v) for k, v in (weights or DEFAULT_WEIGHTS).items() if k in KINDS and v > 0}
        self.query_rules = query_rules
        self.alts = {a.uid: a for vs in grammar.rules.values() for v in vs for a in v.alts}

    # ---- entry point
    def checks(self, index: int, tree: Node, toks: list[str], sql: str, schema: Schema) -> list[Check]:
        """Checks for statement ``index`` (``tree`` produced ``toks``, rendered as ``sql``)."""
        if self.per_query <= 0 or not self.weights or not eligible(sql):
            return []
        root = tree.kids[0] if tree.kids and tree.kids[0] is not None else None
        if root is None or root.sym not in self.query_rules:
            return []
        t = _Tree(tree, toks, self.alts)
        builders = {"tlp_where": self._tlp_where, "tlp_having": self._tlp_having, "norec": self._norec,
                    "expr": self._expr, "cte_materialize": self._cte, "table_fence": self._fence}
        kinds = list(self.weights)
        out: list[Check] = []
        tried: set[str] = set()
        while len(out) < self.per_query and len(tried) < len(kinds):
            left = [k for k in kinds if k not in tried]
            k = self.rng.choices(left, weights=[self.weights[x] for x in left])[0]
            tried.add(k)
            built = builders[k](t, root, schema)
            if built is None:
                continue
            kind, lhs, rhs = built
            lhs_sql = render(lhs) if lhs is not None else None
            rhs_sql = render(rhs)
            if rhs_sql == (lhs_sql or sql):
                continue
            mask = masks_floats(lhs_sql or sql) or masks_floats(rhs_sql)
            out.append(Check(index, kind, lhs_sql, rhs_sql, mask))
        return out

    # ---- helpers
    # Rules whose select_core result is used as a multiset by the enclosing query,
    # so replacing it by an equal multiset cannot change the statement's result.
    MULTISET_CONTEXTS = frozenset({"query", "subquery", "set_arm", "in_sub", "exists_sub", "lateral_subquery"})

    def _core(self, t: _Tree, root: Node) -> Node | None:
        """The select_core of the query itself (not of a CTE, subquery or set arm)."""
        core = t.child(root, "select_core")
        return core if core is not None and t.region(core) else None

    def _cores(self, t: _Tree, root: Node, grouped: bool, clause: str) -> list[Node]:
        """select_cores in a multiset context that have ``clause`` (and are grouped or not)."""
        out = []
        for n in t.nodes:
            if n.sym != "select_core" or not t.region(n):
                continue
            parent = t.parent.get(id(n))
            while parent is not None and parent.sym in ("#rep", "#grp"):
                parent = t.parent.get(id(parent))
            if parent is None or parent.sym not in self.MULTISET_CONTEXTS:
                continue
            if (self._grouping(t, n) != "none") != grouped or self._has_window(t, n):
                continue
            c = t.child(n, clause)
            if c is not None and t.region(c) and t.child(c, "expr") is not None:
                out.append(n)
        return out

    def _grouping(self, t: _Tree, core: Node) -> str:
        b = t.alt_builtins(core)
        return "groups" if "group_keys" in b else "global" if "global_agg" in b else "none"

    def _items_types(self, t: _Tree, core: Node) -> tuple[str, ...] | None:
        items = t.child(core, "@items")
        return items.val if items is not None and isinstance(items.val, tuple) else None

    def _has_window(self, t: _Tree, core: Node) -> bool:
        items = t.child(core, "@items")
        return items is not None and t.contains(items, {"win"})

    def _partition(self, t: _Tree, core: Node, clause: Node, keyword: str, union: str, nested: bool) -> list[str]:
        pred = t.child(clause, "expr")
        assert pred is not None
        p = t.tokens(pred) or []
        start, end = t.region(core)  # type: ignore[misc]
        cs, ce = t.region(clause)  # type: ignore[misc]
        arms = []
        for cond in (_paren(p), ["NOT"] + _paren(p), _paren(p) + ["IS", "NULL"]):
            arm = t.toks[start:cs] + [keyword] + cond + t.toks[ce:end]
            arms.append(_paren(arm))
        joined = arms[0] + [union] + arms[1] + [union] + arms[2]
        if nested:   # keep INTERSECT (binds tighter than UNION) from regrouping the arms
            joined = _paren(joined)
        return t.toks[:start] + joined + t.toks[end:]

    # ---- builders: return (kind, lhs tokens or None, rhs tokens) or None
    def _tlp_where(self, t: _Tree, root: Node, schema: Schema):
        cores = self._cores(t, root, grouped=False, clause="where_clause")
        distinct_ok = [c for c in cores if t.child(c, "distinct") is None
                       or set(self._items_types(t, c) or ("?",)) <= UNIQUE_TEXT_TYPES]
        if not distinct_ok:
            return None
        core = self.rng.choice(distinct_ok)
        where = t.child(core, "where_clause")
        distinct = t.child(core, "distinct") is not None
        lhs = t.replace(where, [])  # type: ignore[arg-type]
        rhs = self._partition(t, core, where, "WHERE", "UNION" if distinct else "UNION ALL",  # type: ignore[arg-type]
                              nested=core is not self._core(t, root))
        return "tlp_where", lhs, rhs

    def _tlp_having(self, t: _Tree, root: Node, schema: Schema):
        ok = []
        for core in self._cores(t, root, grouped=True, clause="having_clause"):
            keys = t.child(core, "@group_keys")
            types = []
            for alias, rel, col in (keys.val if keys is not None else []):
                r = schema.relations.get(rel)
                c = r.col(col) if r is not None else None
                types.append(c.type if c is not None else "?")
            if set(types) <= UNIQUE_TEXT_TYPES:
                ok.append(core)
        if not ok:
            return None
        core = self.rng.choice(ok)
        having = t.child(core, "having_clause")
        lhs = t.replace(having, [])  # type: ignore[arg-type]
        rhs = self._partition(t, core, having, "HAVING", "UNION ALL",  # type: ignore[arg-type]
                              nested=core is not self._core(t, root))
        return "tlp_having", lhs, rhs

    def _norec(self, t: _Tree, root: Node, schema: Schema):
        core = self._core(t, root)
        if core is None:
            return None
        where, frm = t.child(core, "where_clause"), t.child(core, "from_clause")
        if where is None or frm is None or not t.region(where) or not t.region(frm):
            return None
        pred = t.child(where, "expr")
        p, f, w = (t.tokens(pred) if pred else None), t.tokens(frm), t.tokens(where)
        if not p or not f or not w:
            return None
        start, _ = t.region(core)  # type: ignore[misc]
        prefix = t.toks[:start]
        lhs = prefix + ["SELECT", "COUNT", "(", "*", ")"] + f + w
        rhs = prefix + ["SELECT", "COALESCE", "(", "SUM", "(", "CASE", "WHEN"] + _paren(p) + \
            ["THEN", "1", "ELSE", "0", "END", ")", ",", "0", ")"] + f
        return "norec", lhs, rhs

    def _expr(self, t: _Tree, root: Node, schema: Schema):
        cands = [n for n in t.nodes if n.sym == "expr" and t.region(n)
                 and not t.contains(n, {"agg", "win", "@sorted_agg"})]
        if not cands:
            return None
        n = self.rng.choice(cands)
        rw = expr_rewrites(n.typ)
        if any(a.sym in ("agg", "win") for a in t.ancestors(n)):
            rw.pop("scalar_sub", None)   # keep sub-selects out of aggregate/window arguments
        name = self.rng.choice(sorted(rw))
        return f"expr:{name}", None, t.replace(n, rw[name](t.tokens(n) or []))

    def _cte(self, t: _Tree, root: Node, schema: Schema):
        ctes = [n for n in t.nodes if n.sym == "cte_def" and t.region(n)]
        if not ctes:
            return None
        n = self.rng.choice(ctes)
        inner = t.tokens(n) or []
        words = [(i, x) for i, x in enumerate(inner) if x and x[0] not in "\x01\x02"]
        at = next((k for k, (_, x) in enumerate(words) if x == "AS"), None)
        if at is None or at + 1 >= len(words):
            return None
        i_next, nxt = words[at + 1]
        if nxt == "(":
            new = inner[:i_next] + ["MATERIALIZED"] + inner[i_next:]
        elif nxt == "MATERIALIZED":
            new = inner[:i_next] + ["NOT"] + inner[i_next:]
        elif nxt == "NOT" and at + 2 < len(words) and words[at + 2][1] == "MATERIALIZED":
            new = inner[:i_next] + inner[words[at + 2][0]:]
        else:
            return None
        return "cte_materialize", None, t.replace(n, new)

    def _fence(self, t: _Tree, root: Node, schema: Schema):
        tabs = []
        for n in t.nodes:
            toks = t.tokens(n) if n.sym == "@table" else None
            if toks and len(toks) == 3 and toks[1] == "AS":
                tabs.append((n, toks))
        if not tabs:
            return None
        n, (rel, _, alias) = self.rng.choice(tabs)
        new = ["(", "SELECT", "*", "FROM", rel, "OFFSET", "0", ")", "AS", alias]
        return "table_fence", None, t.replace(n, new)
