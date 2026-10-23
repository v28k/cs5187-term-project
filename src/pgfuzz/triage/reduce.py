"""Test-case reduction.

Two levels, as in the plan (reduce, then classify, bisect and report):

1. **Statements** (:func:`reduce_statements`): drop whole statements that are not
   needed (ddmin, Zeller and Hildebrandt, TSE 2002), keeping the culprit.
2. **Tokens of one statement** (:class:`TokenReducer`): Hierarchical Delta
   Debugging (Misherghi and Su, ICSE 2006) over the parenthesis tree of the
   statement. Coarse edits first (remove a clause, remove a list element,
   unwrap or replace a parenthesised sub-expression with a small literal), then
   single tokens. An edit is kept only if the reduced test case still
   reproduces *the same* failure (the caller's ``interesting`` predicate).

Differential pairs (a query and an equivalent rewrite of it) are reduced as
one token list containing a :data:`~pgfuzz.triage.sqltok.HOLE`: the two sides
are materialised by substituting each side's text for the hole, so every edit
is applied to both sides at once and they stay equivalent. The hole itself is
never removed.
"""

from __future__ import annotations

import time
from typing import Callable

from pgfuzz.triage.sqltok import HOLE, Tok, clauses, delete_items, levels, list_items, list_regions, matching, render

# Replacements tried for a parenthesised sub-expression or a function call.
SUBSTITUTES = ("NULL", "1", "TRUE", "FALSE", "0", "''")


class TokenReducer:
    def __init__(self, interesting: Callable[[list[Tok]], bool], budget: int = 500,
                 time_budget_s: float = 900, log: Callable[[str], None] | None = None) -> None:
        self.interesting_fn = interesting
        self.budget, self.time_budget_s = budget, time_budget_s
        self.log = log or (lambda s: None)
        self.tests = 0
        self.cache: dict[str, bool] = {}
        self._t0 = 0.0

    # ---- bookkeeping
    def _left(self) -> bool:
        return self.tests < self.budget and time.monotonic() - self._t0 < self.time_budget_s

    def _try(self, cand: list[Tok], cur: list[Tok]) -> bool:
        if not cand or len(cand) >= len(cur) or not self._left():
            return False
        if any(t.kind == "hole" for t in cur) and not any(t.kind == "hole" for t in cand):
            return False
        key = render(cand)
        if key in self.cache:
            return self.cache[key]
        self.tests += 1
        ok = bool(self.interesting_fn(cand))
        self.cache[key] = ok
        return ok

    # ---- passes: each returns a smaller interesting list or None
    def _clauses(self, toks: list[Tok]) -> list[Tok] | None:
        for start, end in levels(toks):
            for a, b in sorted(clauses(toks, start, end), key=lambda r: r[0] - r[1]):
                cand = toks[:a] + toks[b:]
                if self._try(cand, toks):
                    return cand
        return None

    def _items(self, toks: list[Tok]) -> list[Tok] | None:
        regions = [r for start, end in levels(toks) for r in list_regions(toks, start, end)]
        for start, end in regions:
            items = list_items(toks, start, end)
            if len(items) < 2:
                continue
            # halves first (ddmin's coarse step), then single items
            n = len(items)
            spans = ([(0, n // 2 - 1), (n // 2, n - 1)] if n > 3 else []) + [(k, k) for k in range(n)]
            for i, j in spans:
                cand = delete_items(toks, items, i, j)
                if self._try(cand, toks):
                    return cand
        return None

    def _groups(self, toks: list[Tok]) -> list[Tok] | None:
        pairs = sorted(matching(toks).items(), key=lambda p: p[0] - p[1])   # largest first
        for o, c in pairs:
            call = o > 0 and toks[o - 1].kind == "word" and toks[o].text == "("
            inner = toks[o + 1:c]
            starts = [o - 1, o] if call else [o]
            for s in starts:
                for lit in SUBSTITUTES:
                    cand = toks[:s] + [Tok(lit, "word" if lit[0].isalpha() else "num" if lit[0].isdigit() else "str", True)] + toks[c + 1:]
                    if self._try(cand, toks):
                        return cand
            if inner and not call:
                cand = toks[:o] + inner + toks[c + 1:]
                if self._try(cand, toks):
                    return cand
        return None

    def _tokens(self, toks: list[Tok]) -> list[Tok] | None:
        n = len(toks)
        size = max(1, n // 4)
        while size >= 1 and self._left():
            for i in range(0, n - size + 1, size):
                cand = toks[:i] + toks[i + size:]
                if self._try(cand, toks):
                    return cand
            size //= 2
        return None

    def reduce(self, toks: list[Tok]) -> list[Tok]:
        self._t0 = time.monotonic()
        best = list(toks)
        progress = True
        while progress and self._left():
            progress = False
            for name, p in (("clauses", self._clauses), ("items", self._items), ("groups", self._groups),
                            ("tokens", self._tokens)):
                while self._left():
                    new = p(best)
                    if new is None:
                        break
                    self.log(f"  {name}: {len(best)} -> {len(new)} tokens")
                    best = new
                    progress = True
        return best


def reduce_statements(statements: list[str], keep: int, interesting: Callable[[list[str], int], bool],
                      log: Callable[[str], None] | None = None) -> tuple[list[str], int]:
    """ddmin over statements other than ``keep`` (the culprit). ``interesting`` gets the
    candidate list and the culprit's new index. Returns the reduced list and index."""
    log = log or (lambda s: None)
    others = [i for i in range(len(statements)) if i != keep]
    n = 2
    while others:
        chunk = max(1, len(others) // n)
        removed = False
        for start in range(0, len(others), chunk):
            drop = set(others[start:start + chunk])
            cand = [s for i, s in enumerate(statements) if i not in drop]
            new_keep = keep - sum(1 for i in drop if i < keep)
            if interesting(cand, new_keep):
                log(f"  statements: {len(statements)} -> {len(cand)}")
                statements, keep = cand, new_keep
                others = [i for i in range(len(statements)) if i != keep]
                n = max(n - 1, 2)
                removed = True
                break
        if not removed:
            if chunk == 1:
                break
            n = min(n * 2, len(others))
    return statements, keep


def split_pair(a: str, b: str) -> tuple[list[Tok], list[Tok], list[Tok]] | None:
    """Tokens of ``a`` with the region where ``b`` differs replaced by HOLE, plus the
    two differing middles: ``a == prefix + mid_a + suffix``, ``b == prefix + mid_b + suffix``."""
    from pgfuzz.triage.sqltok import lex

    ta, tb = lex(a), lex(b)
    p = 0
    while p < min(len(ta), len(tb)) and ta[p].text == tb[p].text:
        p += 1
    s = 0
    while s < min(len(ta), len(tb)) - p and ta[-1 - s].text == tb[-1 - s].text:
        s += 1
    if p == len(ta) and p == len(tb):
        return None
    skel = ta[:p] + [HOLE] + ta[len(ta) - s:]
    return skel, ta[p:len(ta) - s], tb[p:len(tb) - s]


def fill(skel: list[Tok], mid: list[Tok]) -> list[Tok]:
    out: list[Tok] = []
    for t in skel:
        out.extend(mid if t.kind == "hole" else [t])
    return out
