"""The validation gate: no model output enters the fuzzer unless the server agrees.

A proposal (grammar fragment + seed test cases) for one commit is accepted only if

1. **parse**         the fragment parses together with the grammar, adds no types,
                     and uses only known builtins;
2. **reachability**  sampling with the fragment's alternatives boosted actually
                     derives them (at least ``min_uses`` statements);
3. **validity**      statements that use them run on the server at least
                     ``min_validity`` of the time (PostgreSQL decides, not the model);
4. **seeds**         seed test cases run without error (failing seeds are dropped);
5. **coverage**      (when a coverage build is configured) the fragment covers more
                     of the commit's changed lines than the unchanged grammar with the
                     same sample size. Without a coverage build this check is
                     reported as "not measured" and does not block.

Everything the gate measures is returned, sent back to the model on failure (a
repair round), and stored in the ledger. Bug candidates hit while gating are
recorded too: the gate is also a small fuzzing campaign aimed at the commit.
"""

from __future__ import annotations

import json
import random
import re
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pgfuzz.core.interfaces import Feedback, GeneratorContext
from pgfuzz.core.sqlsplit import split_statements
from pgfuzz.core.types import Outcome, TestCase
from pgfuzz.eval import oracle
from pgfuzz.grammar.dsl import GrammarError, parse_grammar
from pgfuzz.grammar.engine import Engine
from pgfuzz.grammar.generator import GrammarGenerator, normalize_message
from pgfuzz.grammar.schema import load_schema
from pgfuzz.llm import diffcov
from pgfuzz.llm.commits import CommitDigest

_DIRECTIVE = re.compile(r"^\s*%(type|start)\b", re.M)


@dataclass
class GateConfig:
    sample_n: int = 150
    min_uses: int = 5
    min_validity: float = 0.6
    boost: float = 25.0
    seed: int = 7
    coverage_build: str | None = None     # PostgreSQL build dir with gcov data (server runs from it)
    pg_repo: str | None = None            # git checkout used to map changed lines to the build's revision
    pg_head: str = "HEAD"
    rewrite_sample: int = 150              # test cases per proposed equivalence rewrite
    max_rewrite_errors: float = 0.2        # share of checks whose rewritten side may fail


@dataclass
class GateReport:
    accepted: bool = False
    accepted_fragment: bool = False
    accepted_seeds: list[str] = field(default_factory=list)
    accepted_rewrites: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"accepted": self.accepted, "accepted_fragment": self.accepted_fragment,
                "accepted_seeds": len(self.accepted_seeds), "accepted_rewrites": len(self.accepted_rewrites),
                **self.details}


class Gate:
    def __init__(self, grammar_path: str | Path, schema_path: str | Path, executor: Any, cfg: GateConfig) -> None:
        self.grammar_path, self.schema_path = str(grammar_path), str(schema_path)
        self.base_text = Path(grammar_path).read_text(encoding="utf-8")
        self.base_lines = self.base_text.count("\n") + 1
        self.ex = executor
        self.cfg = cfg
        self._baseline: dict[str, dict] = {}

    # ---- 1. parse
    def _parse(self, fragment: str) -> str | None:
        if _DIRECTIVE.search(fragment):
            return "the fragment must not contain %type or %start lines"
        try:
            g = parse_grammar(self.base_text + "\n" + fragment, "grammar+fragment")
            Engine(g, load_schema(self.schema_path), random.Random(0))
        except (GrammarError, ValueError) as e:
            return str(e)[:600]
        if not any(a.line > self.base_lines for vs in g.rules.values() for v in vs for a in v.alts):
            return "the fragment defines no alternatives"
        return None

    # ---- 2+3. sample with the fragment boosted, run on the server
    def _generator(self, fragment: str | None, workdir: Path) -> GrammarGenerator:
        extra = []
        if fragment:
            f = workdir / "fragment.pgg"
            f.write_text(fragment, encoding="utf-8")
            extra = [str(f)]
        gen = GrammarGenerator(self.grammar_path, self.schema_path, mutate_prob=0.0, extra_grammars=extra)
        gen.setup(GeneratorContext(self.cfg.seed, random.Random(self.cfg.seed), workdir))
        return gen

    def _run_sample(self, gen: GrammarGenerator, frag_uids: set[int]) -> dict[str, Any]:
        for uid in frag_uids:
            gen.engine.alt_boost[uid] = self.cfg.boost
        errors: Counter[str] = Counter()
        bugs = []
        for i in range(self.cfg.sample_n):
            tc = gen.next_testcase()
            if tc is None:
                break
            tc.id = i
            res = self.ex.execute(tc)
            cls = oracle.classify(res)
            gen.feedback(Feedback(tc, res, cls.outcome, cls.statement_outcomes, frozenset(), False))
            built_uses = any(gen.alt_use[u] for u in frag_uids)
            for st, oc in zip(res.statements, cls.statement_outcomes):
                if oc is not Outcome.OK and st.message and built_uses:
                    errors[f"{oc.value}: {normalize_message(st.message)}"] += 1
            if cls.is_bug_candidate:
                bugs.append({"outcome": cls.outcome.value, "message": cls.message,
                             "culprit_sql": tc.statements[cls.culprit] if cls.culprit is not None else None})
        uses = sum(gen.alt_use[u] for u in frag_uids)
        ok = sum(gen.alt_ok[u] for u in frag_uids)
        per_alt = {gen.alt_where.get(u, str(u)): f"{gen.alt_ok[u]}/{gen.alt_use[u]}" for u in sorted(frag_uids)}
        return {"uses": uses, "ok": ok, "validity": round(ok / uses, 3) if uses else 0.0, "per_alternative": per_alt,
                "top_errors": dict(errors.most_common(8)), "bug_candidates": bugs}

    # ---- 4. seeds
    def _seeds(self, seeds: list[str]) -> tuple[list[str], list[dict]]:
        good, info = [], []
        for i, s in enumerate(seeds):
            stmts = split_statements(s)
            if not stmts:
                continue
            res = self.ex.execute(TestCase(stmts, origin="llm-seed", id=i))
            cls = oracle.classify(res)
            bad = [(j, st.sqlstate, st.message) for j, st in enumerate(res.statements) if st.status.value != "ok"]
            info.append({"seed": i, "ok": not bad and not cls.is_bug_candidate, "outcome": cls.outcome.value,
                         "errors": [f"stmt {j}: {code} {msg}" for j, code, msg in bad[:3]]})
            if cls.is_bug_candidate:
                info[-1]["bug_candidate"] = {"outcome": cls.outcome.value, "message": cls.message}
            if not bad:
                good.append(s)
        return good, info

    # ---- 5. diff coverage
    def _coverage(self, commit: CommitDigest, run) -> dict[str, Any]:
        build = self.cfg.coverage_build
        diffcov.reset(build)  # type: ignore[arg-type]
        run()
        if hasattr(self.ex, "reconnect"):
            self.ex.reconnect()
        return diffcov.diff_coverage(build, commit.targets, self.cfg.pg_repo, commit.sha, self.cfg.pg_head)  # type: ignore[arg-type]

    # ---- equivalence rewrites (the LLM extends the oracle, not only the grammar)
    _VOLATILE = re.compile(r"\b(random|now|clock_timestamp|nextval|setseed|txid_current|pg_sleep)\b", re.I)

    def check_rewrites(self, rewrites: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Soundness test of each proposed rewrite on the server: apply only it, with
        confirmation re-runs, to the expressions of ``rewrite_sample`` test cases. Accepted
        only with >= ``min_uses`` checks, few errors and *no* confirmed mismatch."""
        accepted, info = [], []
        types = set(load_grammar_types(self.grammar_path))
        base = getattr(self.ex, "test", self.ex)
        saved = (getattr(base, "mm_enabled", False), getattr(base, "mm_confirm", False))
        base.mm_enabled, base.mm_confirm = True, True
        try:
            for r in rewrites[:3]:
                name = re.sub(r"\W+", "_", str(r.get("name") or "rw")).strip("_")[:40] or "rw"
                typ, tpl = str(r.get("type", "")), str(r.get("template", ""))
                rec: dict[str, Any] = {"name": name, "type": typ, "template": tpl}
                problem = (f"unknown type {typ!r} (use a %type name: {', '.join(sorted(types))})" if typ not in types
                           else "the template must contain {e}" if "{e}" not in tpl
                           else "unbalanced parentheses" if tpl.count("(") != tpl.count(")")
                           else "volatile function" if self._VOLATILE.search(tpl)
                           else "explicit COLLATE: the rewrite would change the collation its input is compared "
                                "or folded with (an identity must keep it)" if re.search(r"\bCOLLATE\b", tpl, re.I)
                           else None)
                if problem:
                    info.append({**rec, "accepted": False, "reason": problem})
                    continue
                counter = self._probe(typ, tpl)
                if counter is not None:
                    info.append({**rec, "accepted": False, "reason": counter})
                    continue
                f = Path(tempfile.mkdtemp(prefix="pgfuzz-rw-")) / "rw.json"
                f.write_text(json.dumps({"rewrites": [{"name": name, "type": typ, "template": tpl}]}), encoding="utf-8")
                gen = GrammarGenerator(self.grammar_path, self.schema_path, mutate_prob=0.0, mm_prob=1.0,
                                       mm_weights={"expr": 1.0}, extra_rewrites=[str(f)], only_rewrite=f"llm_{name}")
                gen.setup(GeneratorContext(self.cfg.seed, random.Random(self.cfg.seed), f.parent))
                kind = f"expr:llm_{name}"
                ran = ok = err = mism = 0
                errors: Counter[str] = Counter()
                example = None
                for i in range(self.cfg.rewrite_sample):
                    tc = gen.next_testcase()
                    if not tc.meta.get("checks"):
                        continue
                    tc.id = i
                    res = self.ex.execute(tc)
                    for sql, st in zip(tc.statements, res.statements):
                        for c in st.checks or []:
                            if c.get("kind") != kind:
                                continue
                            ran += 1
                            if c.get("status") == "ok" and c.get("confirmed") and c.get("lhs_hash") != c.get("rhs_hash"):
                                mism += 1
                                example = example or {"query": sql, "rewritten": c.get("rhs_sql")}
                            elif c.get("status") == "ok":
                                ok += 1
                            else:
                                err += 1
                                errors[normalize_message(c.get("message") or "")] += 1
                good = ran >= self.cfg.min_uses and mism == 0 and err <= self.cfg.max_rewrite_errors * ran
                rec.update(checks=ran, equal=ok, errors=err, mismatches=mism, top_errors=dict(errors.most_common(3)),
                           accepted=good)
                if example:
                    rec["mismatch_example"] = example
                    rec["note"] = ("not an identity on this server, or a bug in it: triage the example before "
                                   "discarding it")
                if not good and not mism:
                    rec["reason"] = ("too few uses" if ran < self.cfg.min_uses else "too many errors")
                info.append(rec)
                if good:
                    accepted.append({"name": name, "type": typ, "template": tpl, "why": r.get("why", "")})
        finally:
            base.mm_enabled, base.mm_confirm = saved
        return accepted, info

    def _probe(self, typ: str, tpl: str) -> str | None:
        """Evaluate the rewrite on concrete values (NULL, the type's edges, data quantiles);
        sampling queries alone misses NULL handling, because most predicates sit where
        NULL and false filter the same rows. Returns a counterexample, or None."""
        import psycopg

        from pgfuzz.grammar.profile import TYPE_EDGES, Profile

        sqlt = {t: d.sql for t, d in load_grammar_obj(self.grammar_path).types.items()}[typ]
        vals = [f"NULL::{sqlt}"] + list(TYPE_EDGES.get(typ, []))
        prof = Path(self.schema_path).with_name("profile.json")
        if prof.exists():
            vals += Profile.load(prof).quantile.get(typ, [])[:6]
        base = getattr(self.ex, "test", self.ex)
        if not base._alive():
            base._connect(wait=True)
        for v in vals:
            q = f"SELECT ({tpl.replace('{e}', f'({v})')}) IS NOT DISTINCT FROM ({v})"
            try:
                same = base.conn.execute(q).fetchone()[0]       # autocommit, read-only
            except psycopg.Error as e:
                if not base._alive():
                    base._connect(wait=True)
                return f"for e = {v} the rewrite fails: {str(e).splitlines()[0][:160]}"
            if str(same).lower() not in ("t", "true"):
                return f"not an identity: for e = {v} the rewrite gives a different value"
        return None

    def check(self, fragment: str, seeds: list[str], commit: CommitDigest,
              rewrites: list[dict[str, Any]] | None = None) -> GateReport:
        rep = GateReport()
        d = rep.details
        work = Path(tempfile.mkdtemp(prefix="pgfuzz-gate-"))
        fragment = fragment.strip()
        frag_ok = False
        sample: dict[str, Any] = {}
        if fragment:
            err = self._parse(fragment)
            d["parse"] = "ok" if err is None else err
            if err is None:
                gen = self._generator(fragment, work)
                uids = {a.uid for vs in gen.grammar.rules.values() for v in vs for a in v.alts
                        if a.line > self.base_lines}
                sample = self._run_sample(gen, uids)
                d["reachability"] = {"uses": sample["uses"], "per_alternative": sample["per_alternative"]}
                d["validity"] = {"rate": sample["validity"], "top_errors": sample["top_errors"]}
                if sample["bug_candidates"]:
                    d["bug_candidates"] = sample["bug_candidates"][:10]
                frag_ok = sample["uses"] >= self.cfg.min_uses and sample["validity"] >= self.cfg.min_validity
        else:
            d["parse"] = "empty fragment (seeds only)"
        good_seeds, seed_info = self._seeds(seeds)
        d["seeds"] = seed_info
        if rewrites:
            rep.accepted_rewrites, d["rewrites"] = self.check_rewrites(rewrites)

        if self.cfg.coverage_build and (frag_ok or good_seeds):
            def run_llm():
                if frag_ok:
                    g = self._generator(fragment, work)
                    self._run_sample(g, {a.uid for vs in g.grammar.rules.values() for v in vs for a in v.alts
                                         if a.line > self.base_lines})
                self._seeds(good_seeds)
            cov = self._coverage(commit, run_llm)
            if commit.sha not in self._baseline:
                self._baseline[commit.sha] = self._coverage(commit, lambda: self._run_sample(self._generator(None, work), set()))
            base = self._baseline[commit.sha]
            d["coverage"] = {"with_proposal": cov, "baseline": base,
                             "gain_lines": cov["covered"] - base["covered"]}
            gained = cov["covered"] > base["covered"]
            rep.accepted_fragment = frag_ok and gained
            rep.accepted_seeds = good_seeds if gained else []
        else:
            d["coverage"] = "not measured (no coverage build configured)"
            rep.accepted_fragment = frag_ok
            rep.accepted_seeds = good_seeds
        # a proposal with a fragment stands or falls with it (a rejected fragment gets a repair round;
        # its valid seeds are kept regardless); a seeds-only proposal is accepted on its seeds
        rep.accepted = rep.accepted_fragment if fragment else bool(rep.accepted_seeds or rep.accepted_rewrites)
        return rep


def load_grammar_types(path: str) -> list[str]:
    from pgfuzz.grammar.dsl import load_grammar

    return list(load_grammar(path).types)


def load_grammar_obj(path: str):
    from pgfuzz.grammar.dsl import load_grammar

    return load_grammar(path)
