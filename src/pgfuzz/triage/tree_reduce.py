"""Grammar-tree reduction: shrink a failing test case on its derivation trees.

Token-level reduction (``reduce.py``) deletes text and lets the server reject
the many candidates that no longer parse or type-check. Reduction on the tree
cannot produce such candidates: every step replaces a subtree by the smallest
derivation of the same rule and type (an engine ``MINIMAL`` marker), drops one
repetition, or drops a whole statement, and the generator *replays* the trees,
re-binding names, aliases and types. So almost every candidate is valid SQL and
the server's time goes to the question that matters: does the failure remain?

This is the fourth job of the derivation tree (generation, mutation,
metamorphic rewriting, and now reduction). It runs before token reduction,
which then removes what the grammar cannot express as a smaller alternative.
"""

from __future__ import annotations

from typing import Any, Callable

from pgfuzz.grammar.engine import MINIMAL, Fail, Node, minimal_marker, replace_at
from pgfuzz.grammar.generator import GrammarGenerator, _Stmt
from pgfuzz.grammar.treeio import from_json
from pgfuzz.triage.sqltok import lex


def size(sql: list[str]) -> int:
    return sum(len(lex(s)) for s in sql)


def load_trees(meta: dict[str, Any], gen: GrammarGenerator) -> list[_Stmt] | None:
    """The stored trees, if they were made with the same grammar as ``gen``."""
    trees = meta.get("trees")
    m = gen.alt_map()
    if not trees or (meta.get("generator") or {}).get("fingerprint") not in (None, m.fingerprint):
        return None
    return [_Stmt(t["rule"], from_json(t["tree"], m)) for t in trees]  # type: ignore[arg-type]


class TreeReducer:
    def __init__(self, gen: GrammarGenerator, interesting: Callable[[list[str]], bool], budget: int = 300,
                 log: Callable[[str], None] = print) -> None:
        self.gen, self.interesting, self.budget, self.log = gen, interesting, budget, log
        self.runs = 0
        self.derived = 0

    def _derive(self, stmts: list[_Stmt]) -> tuple[list[_Stmt], list[str]] | None:
        self.derived += 1
        try:
            built = self.gen._derive(stmts, strict=True)
        except Fail:
            return None
        return (built.stmts, built.sql) if built.sql else None

    def _moves(self, stmts: list[_Stmt]):
        """Candidate edits, biggest expected gain first."""
        for i in range(len(stmts) - 1, -1, -1):          # drop a whole statement (setup first, from the end)
            if len(stmts) > 1:
                yield stmts[:i] + stmts[i + 1:]
        for i, s in enumerate(stmts):
            nodes = [(p, n) for p, n in s.tree.walk() if p]
            nodes.sort(key=lambda pn: -pn[1].size())
            for p, n in nodes:
                if n.sym == "#rep" and n.kids:            # one repetition fewer
                    for j in range(len(n.kids) - 1, -1, -1):
                        rep = Node(n.sym, n.typ, n.alt, n.kids[:j] + n.kids[j + 1:], n.val, n.tv)
                        yield stmts[:i] + [_Stmt(s.rule, replace_at(s.tree, p, rep))] + stmts[i + 1:]  # type: ignore[arg-type]
                elif n.sym[0] not in "#@" and n.val != MINIMAL and n.size() > 1:
                    yield stmts[:i] + [_Stmt(s.rule, replace_at(s.tree, p, minimal_marker(n)))] + stmts[i + 1:]  # type: ignore[arg-type]

    def reduce(self, stmts: list[_Stmt]) -> tuple[list[_Stmt], list[str]] | None:
        first = self._derive(stmts)
        if first is None or not self.interesting(first[1]):
            self.runs += 1
            self.log("  tree reduction: the replayed trees do not reproduce; skipped")
            return None
        self.runs += 1
        cur, sql = first
        start = size(sql)
        progress = True
        while progress and self.runs < self.budget:
            progress = False
            for cand in self._moves(cur):
                if self.runs >= self.budget:
                    break
                got = self._derive(cand)
                if got is None or size(got[1]) >= size(sql):
                    continue
                self.runs += 1
                if self.interesting(got[1]):
                    cur, sql = got
                    progress = True
                    break                                   # restart from the biggest moves
        self.log(f"  tree reduction: {start} -> {size(sql)} tokens, {len(sql)} statement(s) "
                 f"({self.runs} runs, {self.derived} replays)")
        return cur, sql
