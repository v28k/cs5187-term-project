"""Grammar-based generator (the "Grammar-only" arm, and the base of Grammar + LLM).

A test case is a few *setup* statements (DDL / DML that changes the state the
queries see: indexes, new tables, statistics, ...) followed by one or more
queries, all derived from the ``.pgg`` grammar against the schema in
``schema.yaml``. Schema changes made by earlier statements of a test case are
visible to later ones.

With ``mutate_prob`` > 0 the generator keeps a corpus of interesting test cases
(new SQL features, new feature pairs, new bug signatures, and, when the
executor samples plans, new plan shapes: Query Plan Guidance) and derives new
test cases from them by

* ``regen``   regenerating one subtree of one statement,
* ``splice``  replacing a subtree by a subtree of the same rule and type taken
              from another corpus entry,
* ``insert``  adding a setup statement or a statement from another entry,
* ``drop``    removing a statement.

Mutated trees are replayed through the engine, so names and types are re-bound
and the result is as valid as freshly generated SQL.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pgfuzz.core.interfaces import Feedback, Generator, GeneratorContext
from pgfuzz.core.types import Outcome, TestCase
from pgfuzz.eval.features import feature_pairs, features_of
from pgfuzz.grammar.dsl import Grammar, GrammarError, load_grammar, parse_grammar
from pgfuzz.grammar.engine import Engine, Fail, Node, node_at, render, replace_at
from pgfuzz.grammar.rewrite import Rewriter
from pgfuzz.grammar.schema import Schema, load_schema, validate_schema


@dataclass
class _Stmt:
    rule: str
    tree: Node


@dataclass
class _Entry:
    stmts: list[_Stmt]
    picks: int = 0
    finds: int = 0
    why: str = ""
    sql: list[str] = field(default_factory=list)


@dataclass
class _Built:
    stmts: list[_Stmt]
    sql: list[str]
    owners: list[int] = field(default_factory=list)   # statement index -> tree index
    toks: list[list[str]] = field(default_factory=list)  # statement index -> tokens with span markers
    op: str = "fresh"
    parent: _Entry | None = None


_NORM = [(re.compile(r'"[^"]*"'), '"?"'), (re.compile(r"\b\d+\b"), "N")]


def normalize_message(msg: str) -> str:
    msg = msg.splitlines()[0] if msg else ""
    for rx, rep in _NORM:
        msg = rx.sub(rep, msg)
    return msg[:160]


class GrammarGenerator(Generator):
    name = "grammar"
    REQUIRED_RULES = ("select_item", "insert_value", "insert_query", "assign_value")

    def __init__(
        self,
        grammar: str,
        schema: str,
        start: str | None = None,
        setup_rule: str = "setup_stmt",
        setup_prob: float = 0.5,
        max_setup: int = 2,
        queries: list[int] | tuple[int, int] = (1, 2),
        max_depth: int = 14,
        soft_depth: int = 8,
        mutate_prob: float = 0.5,
        corpus_max: int = 500,
        null_prob: float = 0.06,
        track_alternatives: bool = True,
        mm_prob: float = 0.0,
        mm_per_query: int = 1,
        mm_weights: dict[str, float] | None = None,
        plan_guidance: bool = True,
        extra_grammars: list[str] | str | None = None,
        seeds: list[str] | str | None = None,
        seed_prob: float = 0.05,
    ) -> None:
        self.grammar_path, self.schema_path = grammar, schema
        self.start, self.setup_rule = start, setup_rule
        self.setup_prob, self.max_setup = setup_prob, max_setup
        self.queries = (int(queries[0]), int(queries[1]))
        self.max_depth, self.soft_depth = max_depth, soft_depth
        self.mutate_prob, self.corpus_max, self.null_prob = mutate_prob, corpus_max, null_prob
        self.track_alternatives = track_alternatives
        self.mm_prob, self.mm_per_query, self.mm_weights = float(mm_prob), int(mm_per_query), mm_weights
        self.mm_built: Counter[str] = Counter()
        self.plan_guidance = bool(plan_guidance)
        self.extra_grammars = _paths(extra_grammars, "*.pgg")
        self.seed_paths = _paths(seeds, "*.sql")
        self.seed_prob = float(seed_prob)
        self.fragments_loaded: list[str] = []
        self.fragments_rejected: dict[str, str] = {}
        self.seed_cases: list[list[str]] = []
        self.seen_plans: set[str] = set()
        self.corpus: list[_Entry] = []
        self.pending: dict[int, _Built] = {}
        self.seen_pairs: set[tuple[str, str]] = set()
        self.ops: Counter[str] = Counter()
        self.finds: Counter[str] = Counter()
        self.outcomes: Counter[str] = Counter()
        self.errors: Counter[str] = Counter()
        self.alt_use: Counter[int] = Counter()
        self.alt_ok: Counter[int] = Counter()
        self.gen_failures = 0
        self.n_testcases = 0

    # ------------------------------------------------------------ setup
    def setup(self, ctx: GeneratorContext) -> None:
        super().setup(ctx)
        self.rng = ctx.rng
        self.grammar: Grammar = self._load_grammar()
        self.schema: Schema = load_schema(self.schema_path)
        if self.seed_paths:
            from pgfuzz.core.sqlsplit import split_statements

            for p in self.seed_paths:
                stmts = split_statements(Path(p).read_text(encoding="utf-8"))
                if stmts:
                    self.seed_cases.append(stmts)
        bad = validate_schema(self.schema, set(self.grammar.types))
        if bad:
            raise ValueError(f"{self.schema_path}: {bad}")
        missing = [r for r in self.REQUIRED_RULES if r not in self.grammar.rules]
        if self.setup_rule and self.setup_rule not in self.grammar.rules:
            missing.append(self.setup_rule)
        if missing:
            raise ValueError(f"{self.grammar_path}: missing rules {missing}")
        self.start = self.start or self.grammar.start
        self.engine = Engine(self.grammar, self.schema, self.rng, self.max_depth, self.soft_depth,
                             null_prob=self.null_prob)
        self.alt_where = {a.uid: f"{v.name}:{a.line}" for vs in self.grammar.rules.values()
                          for v in vs for a in v.alts}
        self.rewriter = Rewriter(self.grammar, self.rng, self.mm_per_query, self.mm_weights)

    def _load_grammar(self) -> Grammar:
        """The base grammar plus every extra fragment (LLM arm) that still parses
        together with the ones before it; a fragment that breaks the combination is skipped."""
        if not self.extra_grammars:
            return load_grammar(self.grammar_path)
        text = Path(self.grammar_path).read_text(encoding="utf-8")
        for f in self.extra_grammars:
            frag = Path(f).read_text(encoding="utf-8")
            try:
                g = parse_grammar(text + "\n" + frag, self.grammar_path)
                Engine(g, load_schema(self.schema_path), self.rng)   # unknown builtins
            except (GrammarError, ValueError) as e:
                self.fragments_rejected[Path(f).name] = str(e)[:200]
                continue
            text += f"\n# ---- fragment {Path(f).name}\n" + frag
            self.fragments_loaded.append(Path(f).name)
        return parse_grammar(text, self.grammar_path)

    # ------------------------------------------------------------ generation
    def _derive(self, stmts: list[_Stmt]) -> _Built:
        """(Re)derive a test case from guide trees, in order, with schema state."""
        self.engine.new_testcase()
        out, sql, owners, parts = [], [], [], []
        for s in stmts:
            try:
                tree, toks = self.engine.statement(s.rule, s.tree)
            except Fail:
                self.gen_failures += 1
                continue
            out.append(_Stmt(s.rule, tree))
            for part in _split(toks):
                sql.append(render(part))
                owners.append(len(out) - 1)
                parts.append(part)
        return _Built(out, sql, owners, parts)

    def _fresh_plan(self) -> list[_Stmt]:
        plan = []
        if self.setup_rule and self.rng.random() < self.setup_prob:
            plan += [_Stmt(self.setup_rule, None)] * self.rng.randint(1, self.max_setup)  # type: ignore[arg-type]
        plan += [_Stmt(self.start, None)] * self.rng.randint(*self.queries)  # type: ignore[arg-type]
        return plan

    def _pick_entry(self) -> _Entry:
        weights = [(1 + e.finds) / (1 + e.picks) ** 0.5 for e in self.corpus]
        e = self.rng.choices(self.corpus, weights=weights)[0]
        e.picks += 1
        return e

    def _mutate(self) -> tuple[list[_Stmt], str, _Entry]:
        e = self._pick_entry()
        stmts = list(e.stmts)
        r = self.rng.random()
        if r < 0.55:
            i = self.rng.randrange(len(stmts))
            nodes = [p for p, n in stmts[i].tree.walk() if p and n.sym != "#grp"]
            if nodes:
                p = self.rng.choice(nodes)
                stmts[i] = _Stmt(stmts[i].rule, replace_at(stmts[i].tree, p, None))  # type: ignore[arg-type]
            else:
                stmts[i] = _Stmt(stmts[i].rule, None)  # type: ignore[arg-type]
            return stmts, "regen", e
        if r < 0.8 and len(self.corpus) > 1:
            i = self.rng.randrange(len(stmts))
            targets = [(p, n) for p, n in stmts[i].tree.walk() if p and n.sym[0] not in "#@"]
            donor = self.rng.choice(self.corpus)
            if targets and donor is not e:
                self.rng.shuffle(targets)
                pool: dict[tuple[str, str | None], list[Node]] = {}
                for s in donor.stmts:
                    for _, n in s.tree.walk():
                        if n.sym[0] not in "#@":
                            pool.setdefault((n.sym, n.typ), []).append(n)
                for p, n in targets[:20]:
                    cands = pool.get((n.sym, n.typ))
                    if cands:
                        stmts[i] = _Stmt(stmts[i].rule, replace_at(stmts[i].tree, p, self.rng.choice(cands)))  # type: ignore[arg-type]
                        return stmts, "splice", e
        if r < 0.92 or len(stmts) == 1:
            if self.rng.random() < 0.5 and self.setup_rule:
                stmts.insert(0, _Stmt(self.setup_rule, None))  # type: ignore[arg-type]
            else:
                donor = self.rng.choice(self.corpus)
                s = self.rng.choice(donor.stmts)
                stmts.insert(self.rng.randint(0, len(stmts)), s)
            return stmts[:6], "insert", e
        del stmts[self.rng.randrange(len(stmts))]
        return stmts, "drop", e

    def next_testcase(self) -> TestCase | None:
        if self.seed_cases and self.rng.random() < self.seed_prob:
            self.ops["seed"] += 1
            self.n_testcases += 1
            return TestCase(list(self.rng.choice(self.seed_cases)), origin=self.name, meta={"op": "seed"})
        built = None
        for _ in range(4):
            if self.corpus and self.rng.random() < self.mutate_prob:
                plan, op, parent = self._mutate()
            else:
                plan, op, parent = self._fresh_plan(), "fresh", None
            b = self._derive(plan)
            if b.sql and (parent is None or b.sql != parent.sql):
                b.op, b.parent = op, parent
                built = b
                break
        if built is None:
            built = self._derive(self._fresh_plan())
            if not built.sql:
                built.sql = ["SELECT 1"]
        self.ops[built.op] += 1
        self.n_testcases += 1
        meta: dict[str, Any] = {"op": built.op}
        checks = self._checks(built) if self.mm_prob > 0 else []
        if checks:
            meta["checks"] = checks
        tc = TestCase(built.sql, origin=self.name, meta=meta)
        self.pending[id(tc)] = built
        if len(self.pending) > 64:
            self.pending.pop(next(iter(self.pending)))
        return tc

    def _checks(self, built: _Built) -> list[dict[str, Any]]:
        """Metamorphic follow-ups (see pgfuzz.grammar.rewrite) for some query statements."""
        out: list[dict[str, Any]] = []
        parts_per_tree = Counter(built.owners)
        for i, owner in enumerate(built.owners):
            if parts_per_tree[owner] != 1 or i >= len(built.toks) or self.rng.random() >= self.mm_prob:
                continue
            for c in self.rewriter.checks(i, built.stmts[owner].tree, built.toks[i], built.sql[i], self.engine.schema):
                self.mm_built[c.kind.split(":")[0]] += 1
                out.append(c.to_dict())
        return out

    # ------------------------------------------------------------ feedback
    def feedback(self, fb: Feedback) -> None:
        built = self.pending.pop(id(fb.testcase), None)
        stmt_results = fb.result.statements
        for i, oc in enumerate(fb.statement_outcomes):
            self.outcomes[oc.value] += 1
            if oc is not Outcome.OK and i < len(stmt_results) and stmt_results[i].message:
                self.errors[f"{oc.value}: {normalize_message(stmt_results[i].message)}"] += 1
        if built is None:
            return
        if self.track_alternatives:
            ok_by_tree: dict[int, bool] = {}
            for i, oc in enumerate(fb.statement_outcomes):
                if i < len(built.owners):
                    t = built.owners[i]
                    ok_by_tree[t] = ok_by_tree.get(t, True) and oc is Outcome.OK
            for t, ok in ok_by_tree.items():
                for _, n in built.stmts[t].tree.walk():
                    if n.sym[0] not in "#@":
                        self.alt_use[n.alt] += 1
                        if ok:
                            self.alt_ok[n.alt] += 1
        if self.mutate_prob <= 0:
            return
        feats: set[str] = set()
        for s in fb.testcase.statements:
            feats |= features_of(s)
        new_pairs = feature_pairs(feats) - self.seen_pairs
        self.seen_pairs |= new_pairs
        any_ok = any(oc is Outcome.OK for oc in fb.statement_outcomes)
        plans = {st.plan_shape for st in stmt_results if st.plan_shape} - self.seen_plans
        self.seen_plans |= plans
        why = ("signature" if fb.new_signature else "features" if fb.new_features
               else "pairs" if new_pairs and any_ok
               else "plan" if plans and self.plan_guidance else "")
        if not why:
            return
        if built.parent is not None:
            built.parent.finds += 1
        self.finds[built.op] += 1
        entry = _Entry(built.stmts, why=why, sql=list(fb.testcase.statements))
        self.corpus.append(entry)
        if len(self.corpus) > self.corpus_max:
            weakest = min(range(len(self.corpus) - 1),
                          key=lambda k: (self.corpus[k].why == "signature", self.corpus[k].finds, -self.corpus[k].picks))
            del self.corpus[weakest]

    # ------------------------------------------------------------ reporting
    def stats(self) -> dict[str, Any]:
        if not hasattr(self, "engine"):          # setup() failed; the trial reports that error
            return {"setup": "failed"}
        total = sum(self.outcomes.values())
        worst = []
        for uid, n in self.alt_use.items():
            if n >= 20:
                worst.append((self.alt_ok[uid] / n, n, self.alt_where.get(uid, str(uid))))
        worst.sort()
        return {
            "testcases": self.n_testcases,
            "statements": total,
            "ok_rate": round(self.outcomes.get("ok", 0) / total, 4) if total else None,
            "outcomes": dict(self.outcomes.most_common()),
            "top_errors": dict(self.errors.most_common(25)),
            "worst_alternatives": [f"{w} ok={r:.0%} n={n}" for r, n, w in worst[:25]],
            "ops": dict(self.ops),
            "finds_by_op": dict(self.finds),
            "corpus": len(self.corpus),
            "generation_failures": self.gen_failures,
            "metamorphic_checks_built": dict(self.mm_built),
            "plan_shapes_seen": len(self.seen_plans),
            "fragments_loaded": len(self.fragments_loaded),
            "fragments_rejected": self.fragments_rejected,
            "seed_cases": len(self.seed_cases),
            "corpus_reasons": dict(Counter(e.why for e in self.corpus)),
            **self.engine.stats(),
        }

    def describe(self) -> dict[str, Any]:
        text = Path(self.grammar_path).read_bytes() if Path(self.grammar_path).exists() else b""
        d: dict[str, Any] = {"name": self.name, "grammar": self.grammar_path, "schema": self.schema_path,
                             "grammar_sha1": hashlib.sha1(text).hexdigest()[:12],
                             "mutate_prob": self.mutate_prob, "max_depth": self.max_depth,
                             "setup_prob": self.setup_prob, "queries": list(self.queries),
                             "mm_prob": self.mm_prob, "mm_per_query": self.mm_per_query}
        if self.extra_grammars or self.seed_paths:
            d["fragments"] = [Path(f).name for f in self.extra_grammars]
            d["seed_files"] = len(self.seed_paths)
            d["seed_prob"] = self.seed_prob
        if hasattr(self, "grammar"):
            d["grammar_stats"] = self.grammar.stats()
        return d


def _paths(spec: list[str] | str | None, pattern: str) -> list[str]:
    """Files named directly, or every ``pattern`` file of a named directory (sorted)."""
    if not spec:
        return []
    out: list[str] = []
    for item in [spec] if isinstance(spec, str) else spec:
        p = Path(item)
        out += sorted(str(q) for q in p.glob(pattern)) if p.is_dir() else [str(p)] if p.exists() else []
    return out


def _split(tokens: list[str]) -> list[list[str]]:
    parts: list[list[str]] = [[]]
    for t in tokens:
        if t == ";":
            parts.append([])
        else:
            parts[-1].append(t)
    return [p for p in parts if p]
