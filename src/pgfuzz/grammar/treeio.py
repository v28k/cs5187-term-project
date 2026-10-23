"""Derivation trees to and from JSON, so a failure can be reduced on its tree later.

Alternative uids are process-local (a global counter), so a stored tree names
each alternative by its *ordinal*: its position in a fixed walk over the grammar
(rules, variants, alternatives, nested groups), which is the same for the same
grammar text. ``fingerprint`` records which grammar that is.

Builtin values are tuples (``(alias, rel, col)``, a shape), lists (group keys,
assignments) or sets, and builtins check which one they get when replaying, so
tuples are stored as ``{"tuple": [...]}`` and sets as ``{"set": [...]}``.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pgfuzz.grammar.dsl import Alt, Grammar, Group, Repeat
from pgfuzz.grammar.engine import Node


def _alts(g: Grammar) -> list[Alt]:
    out: list[Alt] = []

    def elems(es: list[object]) -> None:
        for e in es:
            while isinstance(e, Repeat):
                e = e.elem
            if isinstance(e, Group):
                for a in e.alts:
                    out.append(a)
                    elems(a.elems)

    for name in g.rules:
        for v in g.rules[name]:
            for a in v.alts:
                out.append(a)
                elems(a.elems)
    return out


class AltMap:
    def __init__(self, g: Grammar) -> None:
        alts = _alts(g)
        self.to_ord = {a.uid: i for i, a in enumerate(alts)}
        self.to_uid = {i: a.uid for i, a in enumerate(alts)}
        self.fingerprint = hashlib.sha1(
            "|".join(f"{n}:{len(vs)}:{sum(len(v.alts) for v in vs)}" for n, vs in g.rules.items()).encode()
        ).hexdigest()[:12]


def _val_out(v: Any) -> Any:
    # builtins check the container type when they replay (tuple vs list), so keep it
    if isinstance(v, (set, frozenset)):
        return {"set": sorted((_val_out(x) for x in v), key=repr)}
    if isinstance(v, tuple):
        return {"tuple": [_val_out(x) for x in v]}
    if isinstance(v, list):
        return [_val_out(x) for x in v]
    return v


def _val_in(v: Any) -> Any:
    if isinstance(v, dict) and set(v) == {"set"}:
        return frozenset(_val_in(x) for x in v["set"])
    if isinstance(v, dict) and set(v) == {"tuple"}:
        return tuple(_val_in(x) for x in v["tuple"])
    if isinstance(v, list):
        return [_val_in(x) for x in v]
    return v


def to_json(n: Node | None, m: AltMap) -> Any:
    if n is None:
        return None
    d: dict[str, Any] = {"s": n.sym, "a": m.to_ord.get(n.alt, -1), "k": [to_json(k, m) for k in n.kids]}
    if n.typ is not None:
        d["t"] = n.typ
    if n.val is not None:
        d["v"] = _val_out(n.val)
    if n.tv:
        d["tv"] = n.tv
    return d


def from_json(d: Any, m: AltMap) -> Node | None:
    if d is None:
        return None
    return Node(d["s"], d.get("t"), m.to_uid.get(d.get("a", -1), 0), [from_json(k, m) for k in d.get("k", [])],
                _val_in(d.get("v")), d.get("tv"))
