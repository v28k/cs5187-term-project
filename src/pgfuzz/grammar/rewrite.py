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
``tlp_agg``        TLP for aggregates: a global aggregate whose items are all
                   ``MIN/MAX/SUM/COUNT/BIT_*/BOOL_*`` calls equals the combination
                   (MIN of MINs, SUM of COUNTs, ...) over the three WHERE partitions.
``pred:<name>``    Equivalent forms of one predicate node: ``x IN (a, b)`` ->
                   ``(x = a) OR (x = b)`` (PG 18 turns such OR chains back into
                   ``= ANY``), ``a < b`` -> ``NOT (a >= b)``, ``x BETWEEN l AND h`` ->
                   ``x >= l AND x <= h``.
``notnull``        ``WHERE p`` -> ``WHERE p AND c IS NOT NULL`` for a NOT NULL column
                   ``c`` that ``p`` uses (targets NOT NULL based simplification); not
                   under outer joins and not for generated columns.
``order_drop``     Drop the statement's own ORDER BY (the result is a multiset).
``rls``            Row-level security leak oracle: the query run as ``pgfuzz_rls``
                   (policies of corpus/rls.sql apply) equals the query run as
                   superuser with each protected table ``t`` replaced by
                   ``(SELECT * FROM t WHERE <policy>)``.
``cert``           CERT (Ba and Rigger, ICSE 2024): the planner's row estimate of the
                   query must not exceed that of the query without its WHERE; a
                   violation is a performance issue, compared on EXPLAIN only.
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
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable

from pgfuzz.eval.differential import eligible, masks_floats
from pgfuzz.grammar.dsl import Builtin, Grammar
from pgfuzz.grammar.engine import Node, is_marker, node_regions, render
from pgfuzz.grammar.schema import Schema

# Types whose equality implies an identical text form (so DISTINCT / GROUP BY
# may pick any representative of a group without changing the output).
UNIQUE_TEXT_TYPES = frozenset({"int", "bigint", "text", "bool", "date", "tstz", "int4range", "intarr", "textarr"})

KINDS = ("tlp_where", "tlp_having", "tlp_agg", "norec", "expr", "pred", "notnull", "order_drop",
         "cte_materialize", "table_fence", "rls", "cert")
# Partitioning checks apply to fewer queries, so they get the larger weights.
DEFAULT_WEIGHTS = {"tlp_where": 6.0, "tlp_having": 5.0, "tlp_agg": 5.0, "norec": 3.0, "expr": 3.0,
                   "pred": 3.0, "notnull": 1.5, "order_drop": 1.0, "cte_materialize": 1.5, "table_fence": 1.5,
                   "rls": 2.0, "cert": 1.0}
RLS_ROLE = "pgfuzz_rls"
_POLICY = re.compile(r"^CREATE POLICY \w+ ON (\w+) USING \((.*)\);\s*$", re.M)


def load_policies(path: str | None) -> dict[str, str]:
    """``table -> USING predicate`` from the CREATE POLICY lines of an RLS setup file."""
    if not path:
        return {}
    from pathlib import Path

    return {t: pred for t, pred in _POLICY.findall(Path(path).read_text(encoding="utf-8"))}

# Aggregates whose value over a multiset equals COMBINE over the values of its parts.
_AGG_COMBINE = {"MIN": "MIN", "MAX": "MAX", "SUM": "SUM", "COUNT": "SUM", "BIT_OR": "BIT_OR",
                "BIT_AND": "BIT_AND", "BIT_XOR": "BIT_XOR", "BOOL_AND": "BOOL_AND", "BOOL_OR": "BOOL_OR",
                "EVERY": "BOOL_AND"}


def _combinable_items(words: list[str]) -> list[tuple[str, str]] | None:
    """For a select list whose every item is ``AGG ( ... ) AS cN`` with a combinable AGG
    (no DISTINCT, FILTER or ORDER BY), the (combiner, alias) per item; else None."""
    items, cur, depth = [], [], 0
    for w in words:
        if w == "," and depth == 0:
            items.append(cur)
            cur = []
            continue
        depth += (w == "(") - (w == ")")
        cur.append(w)
    items.append(cur)
    out = []
    for it in items:
        if len(it) < 6 or it[-2] != "AS" or it[1] != "(" or it[-3] != ")" or it[0].upper() not in _AGG_COMBINE:
            return None
        if it[2] == "DISTINCT" or "ORDER" in it or "FILTER" in it:
            return None
        d = 0
        for j, w in enumerate(it[1:-2], 1):
            d += (w == "(") - (w == ")")
            if d == 0 and j != len(it) - 3:
                return None            # the call closes before the end: AGG(..) + 1 is not one call
        out.append((_AGG_COMBINE[it[0].upper()], it[-1]))
    return out
# a OP b  ==  NOT (a NEG b)  under three-valued logic, for every type with a btree total order.
_NEGATE = {"=": "<>", "<>": "=", "<": ">=", ">": "<=", "<=": ">", ">=": "<"}


@dataclass
class Check:
    stmt: int                 # index of the statement in the test case
    kind: str                 # e.g. "tlp_where", "expr:scalar_sub"
    lhs: str | None           # None: the statement itself
    rhs: str
    mask: bool = False        # mask float columns when digesting both sides
    lhs_role: str | None = None   # run the left side as this role (RLS oracle)

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

    def direct(self, n: Node) -> list[Node]:
        """Child nodes of ``n``, looking through ``?``/``*`` and groups."""
        out: list[Node] = []
        for k in n.kids:
            if k is None:
                continue
            if k.sym in ("#rep", "#grp"):
                out += self.direct(k)
            else:
                out.append(k)
        return out

    def slots(self, n: Node) -> list[str | Node] | None:
        """The words of ``n`` with every direct child collapsed to its node, e.g.
        ``["(", <expr>, "IN", "(", <expr>, ",", <expr>, ")", ")"]``."""
        r = self.region(n)
        if r is None:
            return None
        starts = {}
        for k in self.direct(n):
            kr = self.region(k)
            if kr is None:
                return None
            starts[kr[0]] = (k, kr[1])
        out: list[str | Node] = []
        i = r[0] + 1 if is_marker(self.toks[r[0]]) else r[0]
        end = r[1]
        while i < end:
            if i in starts:
                k, e = starts[i]
                out.append(k)
                i = e
                continue
            if not is_marker(self.toks[i]):
                out.append(self.toks[i])
            i += 1
        return out

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
                 weights: dict[str, float] | None = None, query_rules: tuple[str, ...] = ("query",),
                 policies: dict[str, str] | None = None) -> None:
        self.rng = rng
        self.policies = dict(policies or {})
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
        builders = {"tlp_where": self._tlp_where, "tlp_having": self._tlp_having, "tlp_agg": self._tlp_agg,
                    "norec": self._norec, "expr": self._expr, "pred": self._pred, "notnull": self._notnull,
                    "order_drop": self._order_drop, "cte_materialize": self._cte, "table_fence": self._fence,
                    "rls": self._rls, "cert": self._cert}
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
            role = None
            if kind == "rls":                 # same SQL on both sides is the point here
                lhs_sql, role = sql, RLS_ROLE
            elif rhs_sql == (lhs_sql or sql):
                continue
            mask = masks_floats(lhs_sql or sql) or masks_floats(rhs_sql)
            out.append(Check(index, kind, lhs_sql, rhs_sql, mask, role))
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
        # HAVING TRUE, not no HAVING: without GROUP BY, a HAVING clause is what makes the level a
        # single-group aggregate (one row even when WHERE removes every row); dropping it would
        # change the query, not just the predicate.
        lhs = t.replace(having, ["HAVING", "TRUE"])  # type: ignore[arg-type]
        rhs = self._partition(t, core, having, "HAVING", "UNION ALL",  # type: ignore[arg-type]
                              nested=core is not self._core(t, root))
        return "tlp_having", lhs, rhs

    def _tlp_agg(self, t: _Tree, root: Node, schema: Schema):
        """TLP for aggregates: ``SELECT AGG(e) FROM f`` equals COMBINE over the three
        partitions of ``f`` by the WHERE predicate (MIN of MINs, SUM of COUNTs, ...)."""
        core = self._core(t, root)
        if core is None or self._grouping(t, core) != "global" or t.child(core, "having_clause") is not None:
            return None
        where, items = t.child(core, "where_clause"), t.child(core, "@items")
        if where is None or items is None or t.child(where, "expr") is None or t.child(core, "distinct") is not None:
            return None
        combine = _combinable_items([x for x in (t.tokens(items) or []) if not is_marker(x)])
        if combine is None:
            return None
        start, end = t.region(core)  # type: ignore[misc]
        lhs = t.replace(where, [])  # type: ignore[arg-type]
        part = self._partition(t, core, where, "WHERE", "UNION ALL", nested=False)  # type: ignore[arg-type]
        arms = part[start:len(part) - (len(t.toks) - end)]
        sel: list[str] = []
        for k, (comb, alias) in enumerate(combine):
            sel += ([","] if k else []) + [comb, "(", "tlp_agg", ".", alias, ")", "AS", alias]
        new = ["SELECT"] + sel + ["FROM", "("] + arms + [")", "AS", "tlp_agg"]
        return "tlp_agg", lhs, t.toks[:start] + new + t.toks[end:]

    def _pred(self, t: _Tree, root: Node, schema: Schema):
        """Equivalent forms of one predicate node: IN list <-> OR chain (PG 18 turns OR
        chains into = ANY), comparison <-> negated complement, BETWEEN <-> two bounds."""
        cands = []
        for n in t.nodes:
            if n.sym != "expr" or n.typ != "bool":
                continue
            sl = t.slots(n)
            if not sl or sl[0] != "(" or sl[-1] != ")":
                continue
            body = sl[1:-1]
            tok = lambda x: t.tokens(x) if isinstance(x, Node) else None   # noqa: E731
            # ( e [NOT] IN ( a , b , ... ) )
            if len(body) >= 5 and isinstance(body[0], Node) and body[-1] == ")" and "IN" in body[1:3]:
                neg = body[1] == "NOT"
                rest = body[(3 if neg else 2):]
                if rest and rest[0] == "(" and all(isinstance(x, Node) for x in rest[1:-1:2]) \
                        and all(x == "," for x in rest[2:-1:2]):
                    e, opts = tok(body[0]), [tok(x) for x in rest[1:-1:2]]
                    if e and all(opts):
                        ors: list[str] = []
                        for k, o in enumerate(opts):
                            ors += (["OR"] if k else []) + ["("] + _paren(e) + ["="] + _paren(o) + [")"]  # type: ignore[operator]
                        cands.append(("in_or", n, (["(", "NOT"] if neg else ["("]) + _paren(ors) + [")"]))
            # ( a cmp b ), cmp a direct child rule
            if len(body) == 3 and all(isinstance(x, Node) for x in body) and body[1].sym == "cmp":
                op = " ".join(w for w in (tok(body[1]) or []) if not is_marker(w))
                a, b = tok(body[0]), tok(body[2])
                if op in _NEGATE and a and b:
                    cands.append(("cmp_negate", n, ["(", "NOT", "("] + _paren(a) + [_NEGATE[op]] + _paren(b) + [")", ")"]))
            # ( x BETWEEN lo AND hi )
            if len(body) == 5 and body[1] == "BETWEEN" and body[3] == "AND" \
                    and all(isinstance(body[i], Node) for i in (0, 2, 4)):
                x, lo, hi = tok(body[0]), tok(body[2]), tok(body[4])
                if x and lo and hi:
                    cands.append(("between", n, ["(", "("] + _paren(x) + [">="] + _paren(lo) + [")", "AND", "("]
                                  + _paren(x) + ["<="] + _paren(hi) + [")", ")"]))
        if not cands:
            return None
        name, n, new = self.rng.choice(cands)
        return f"pred:{name}", None, t.replace(n, new)

    def _notnull(self, t: _Tree, root: Node, schema: Schema):
        """``WHERE p`` -> ``WHERE (p AND c IS NOT NULL)`` for a NOT NULL column ``c`` that
        ``p`` already uses (targets NOT NULL based simplification). Not under outer joins,
        where a NOT NULL column can still be NULL-extended."""
        out = []
        for core in self._cores(t, root, grouped=False, clause="where_clause") + \
                self._cores(t, root, grouped=True, clause="where_clause"):
            frm, where = t.child(core, "from_clause"), t.child(core, "where_clause")
            if frm is None or where is None or set(t.tokens(frm) or []) & {"LEFT", "RIGHT", "FULL"}:
                continue
            pred = t.child(where, "expr")
            if pred is None:
                continue
            for _, m in pred.walk():
                if m.sym == "@col" and isinstance(m.val, tuple) and not self._nested_under(t, m, pred):
                    rel = schema.relations.get(m.val[1])
                    c = rel.col(m.val[2]) if rel is not None else None
                    # generated columns excluded: a partition may compute them differently (d8444163)
                    if c is not None and c.flags & {"notnull", "identity"} and "generated" not in c.flags \
                            and t.tokens(m):
                        out.append((pred, t.tokens(m)))
        if not out:
            return None
        pred, col = self.rng.choice(out)
        new = ["("] + _paren(t.tokens(pred) or []) + ["AND", "("] + [w for w in col if not is_marker(w)] + \
              ["IS", "NOT", "NULL", ")", ")"]
        return "notnull", None, t.replace(pred, new)

    # rules that open a scope (@scope in the grammar): their columns are not visible outside
    _NESTED = frozenset({"select_core", "query", "subquery", "in_sub", "exists_sub", "lateral_subquery", "set_arm",
                         "scalar_sub", "subquery_one"})

    def _nested_under(self, t: _Tree, m: Node, top: Node) -> bool:
        """Is ``m`` inside a sub-select below ``top`` (so its columns are not in ``top``'s scope)?"""
        for a in t.ancestors(m):
            if a is top:
                return False
            if a.sym in self._NESTED:
                return True
        return False

    def _order_drop(self, t: _Tree, root: Node, schema: Schema):
        """The statement's own ORDER BY cannot change its multiset (no LIMIT: eligible)."""
        ob = t.child(root, "order_by")
        if ob is None or not t.region(ob):
            return None
        return "order_drop", None, t.replace(ob, [])

    def _rls(self, t: _Tree, root: Node, schema: Schema):
        """RLS leak oracle: the query as a restricted role (policies apply) must equal the
        query as superuser with every protected table replaced by its filtered rows."""
        if not self.policies:
            return None
        hits = []
        for n in t.nodes:
            toks = t.tokens(n) if n.sym == "@table" else None
            if toks:
                words = [w for w in toks if not is_marker(w)]
                if len(words) == 3 and words[1] == "AS" and words[0] in self.policies:
                    hits.append((t.region(n), words))
        if not hits:
            return None
        out = list(t.toks)
        for (start, end), (rel, _, alias) in sorted(hits, key=lambda h: -h[0][0]):   # right to left
            out[start:end] = ["(", "SELECT", "*", "FROM", rel, "WHERE", "(", self.policies[rel], ")", ")", "AS", alias]
        return "rls", None, out

    def _cert(self, t: _Tree, root: Node, schema: Schema):
        """CERT (Ba and Rigger, ICSE 2024): restricting a query must not raise the planner's
        row estimate. lhs: the query without its WHERE, rhs: the query; compared on
        EXPLAIN estimates, not on results."""
        core = self._core(t, root)
        if core is None or self._grouping(t, core) != "none" or t.child(core, "distinct") is not None \
                or self._has_window(t, core):
            return None
        where = t.child(core, "where_clause")
        if where is None or not t.region(where):
            return None
        return "cert", t.replace(where, []), list(t.toks)

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
