"""Rule kernels: minimal firing witnesses of optimizer rules, and their compositions.

An optimizer bug often needs two rules to meet in one query. Engines do not export what a rule
matches (SQL Server's testing framework reads the rule patterns from the optimizer; ARG abstracts
rules from a rewriter's source), so we learn it from behaviour:

* **Mining.** When a rule fires for a generated query (``Driver.fired``: the plan changes when
  the rule is switched off, or the engine's per-rule trace shows a change), the query's
  derivation tree is reduced with the predicate "the rule still fires". The result is a
  *kernel*: a smallest query we can derive that triggers the rule. Reduction replays typed
  trees, so every candidate is valid SQL.
* **Composition.** Two kernels are combined by templates whose result is determined by the
  results of the parts (a cross join has ``|A| * |B|`` rows, ``UNION ALL`` has ``|A| + |B|``,
  ...). Each composition is a test case with a built-in oracle (the *composition oracle*) and,
  through the executor's plan variants, a rule-ablation oracle. The set of rules that fire for
  the composition gives rule-pair coverage.

Compositions are written as seed files (``-- pgfuzz:check kernel:<template> <expected>``), so
campaigns, crash isolation, triage and ``hunt`` handle them like any other test case.
"""

from __future__ import annotations

import json
import random
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

from pgfuzz.eval.differential import eligible


def _is_query(sql: str) -> bool:
    return sql.lstrip()[:6].upper() in ("SELECT", "VALUES") or sql.lstrip()[:4].upper() == "WITH"


def _one_line(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip().rstrip(";")


class Lab:
    """One engine, in this process, for probing: which rules fire, how many rows a query has."""

    def __init__(self, config: str, name: str | None = None) -> None:
        from pgfuzz.cli import _executor_from
        from pgfuzz.targets.base import load_driver

        ex = _executor_from(config, name)
        if not hasattr(ex, "driver_path"):
            raise SystemExit("rule kernels need an in-process engine target (pgfuzz.targets.*)")
        self.driver = load_driver(ex.driver_path, ex.driver_params)
        self.version = self.driver.connect(list(ex.setup_sql))
        self.rules = list(self.driver.rules())
        self.engine = self.driver.name

    def _in_case(self, setup: list[str], fn: Callable[[], Any]) -> Any:
        d = self.driver
        self.last_error: tuple[str, str] | None = None
        try:
            d.begin()
            done: list[str] = []
            for s in setup:
                try:
                    d.execute(s, False, 0)
                    done.append(s)
                except Exception:
                    # A failing setup statement is left out. Where an error aborts the
                    # transaction (DuckDB), rebuild it from the statements that succeeded.
                    if getattr(d, "error_aborts_transaction", True):
                        d.end()
                        d.begin()
                        for t in done:
                            d.execute(t, False, 0)
            return fn()
        except BaseException as e:           # engine errors of every kind: this probe just says "no"
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            self.last_error = (str(d.error_name(e) or type(e).__name__), str(e)[:300])
            return None
        finally:
            # Roll back first: on an aborted transaction (DuckDB) resetting settings fails, and a
            # skipped ROLLBACK would leave every later probe in the aborted transaction.
            for step in (d.end, d.reset_variant):
                try:
                    step()
                except Exception:
                    pass

    def fired(self, setup: list[str], query: str, rules: list[str] | None = None) -> set[str] | None:
        got = self._in_case(setup, lambda: self.driver.fired(query, rules))
        return None if got is None else set(got[1])

    def rows(self, setup: list[str], query: str) -> list[tuple] | None:
        got = self._in_case(setup, lambda: self.driver.execute(query, True, 100000))
        if got is None or got[0] is None:
            return None
        return sorted((tuple(map(repr, r)) for r in got[0]))


def cap_memory(gb: float | None) -> None:
    """Probes run in this process, and engine tests include deliberately huge queries: cap the
    address space, so an allocation failure is an engine error (the probe says "no") instead of
    the kernel killing the process."""
    if not gb:
        return
    import resource

    lim = int(gb * 2**30)
    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (lim if hard == resource.RLIM_INFINITY else min(lim, hard), hard))


def _generator(config: str, name: str | None, seed: int):
    from pgfuzz.core.interfaces import Generator, GeneratorContext
    from pgfuzz.core.plugins import instantiate
    from pgfuzz.runner import load_config

    cfg = load_config(config)
    fc = next((c for c in cfg.configs if c.name == name), None) if name else cfg.configs[0]
    gen = instantiate(fc.generator.plugin, Generator, fc.generator.render(**cfg.substitutions(fc.name, 0, 0)))
    gen.setup(GeneratorContext(seed, random.Random(seed), Path(tempfile.mkdtemp(prefix="pgfuzz-kernels-"))))
    return gen


def _split(sqls: list[str]) -> list[tuple[list[str], str]]:
    """(setup statements before it, query) for every deterministic query of a test case."""
    out, setup = [], []
    for s in sqls:
        if _is_query(s):
            if eligible(s):
                out.append((list(setup), s))
        else:
            setup.append(s)
    return out


def mine(config: str, n: int = 300, seed: int = 1, per_rule: int = 2, budget: int = 80, name: str | None = None,
         log: Callable[[str], None] = print, mem_limit_gb: float | None = None) -> dict[str, Any]:
    """Generate ``n`` test cases; keep up to ``per_rule`` kernels for every rule that fires."""
    from pgfuzz.triage.tree_reduce import TreeReducer, load_trees, size

    cap_memory(mem_limit_gb)
    lab, gen = Lab(config, name), _generator(config, name, seed)
    spell = getattr(gen, "_dialectize", lambda sqls: list(sqls))    # replayed trees are in the base dialect
    kernels: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    fires: dict[str, int] = {}
    probes = 0
    for _ in range(n):
        tc = gen.next_testcase()
        if tc is None:
            break
        meta = gen.failure_meta(tc) if hasattr(gen, "failure_meta") else {}
        getattr(gen, "pending", {}).pop(id(tc), None)
        k = int(tc.meta.get("synth", 0))
        parts = _split(list(tc.statements[k:]))
        want: set[str] = set()
        before: dict[str, int] = {}
        for setup, q in parts:
            f = lab.fired(setup, q)
            if f is None:
                continue
            probes += 1
            for r in f:
                fires[r] = fires.get(r, 0) + 1
                if len(kernels.get(r, [])) < per_rule:
                    want.add(r)
                    before.setdefault(r, size([q]))
        if not want or k:
            continue
        trees = load_trees(meta, gen) if meta else None
        for r in sorted(want):
            def interesting(sqls: list[str], r: str = r) -> bool:
                return any(r in (lab.fired(s, q, [r]) or ()) for s, q in _split(spell(sqls)))

            sqls = list(tc.statements)
            if trees:
                red = TreeReducer(gen, interesting, budget=budget, log=lambda _m: None).reduce(trees)
                if red is not None:
                    sqls = spell(red[1])
            hit = next(((s, q) for s, q in _split(sqls) if r in (lab.fired(s, q, [r]) or ())), None)
            if hit is None or _one_line(hit[1]) in seen or lab.rows(hit[0], hit[1]) is None:
                continue                                  # a kernel must also execute
            seen.add(_one_line(hit[1]))
            all_fired = lab.fired(hit[0], hit[1]) or {r}
            kernels.setdefault(r, []).append({
                "rule": r, "setup": [_one_line(s) for s in hit[0]], "query": _one_line(hit[1]),
                "tokens": size([hit[1]]), "tokens_before": before.get(r, 0),
                "fired": sorted(all_fired), "reduced_on_tree": bool(trees)})
            log(f"kernel {r}: {kernels[r][-1]['tokens']} tokens: {kernels[r][-1]['query'][:110]}")
    return {"engine": lab.engine, "version": lab.version, "rules": lab.rules, "probed_queries": probes,
            "fires": dict(sorted(fires.items())), "never_fired": sorted(set(lab.rules) - set(fires)),
            "kernels": kernels}


def mine_suite(config: str, seed_files: list[str | Path], mined: dict[str, Any], per_rule: int = 2,
               budget: int = 300, name: str | None = None, max_queries: int = 20000,
               mem_limit_gb: float | None = 3.0, log: Callable[[str], None] = print) -> dict[str, Any]:
    """Kernels for rules the grammar never fired, taken from an engine's own tests.

    ``seed_files`` are imported test files (``pgfuzz import-tests``: one file per test, setup and
    queries in order). Every deterministic query is probed; a query that fires a rule without a
    kernel in ``mined`` is reduced on its tokens with the predicate "the rule still fires and the
    query still runs", and the result is added to ``mined["kernels"]`` (marked ``source: suite``).
    The test's setup statements are kept as they are (they create the tables the query reads)."""
    from pgfuzz.triage.reduce import TokenReducer
    from pgfuzz.triage.sqltok import lex, render

    cap_memory(mem_limit_gb)
    lab = Lab(config, name)
    kernels: dict[str, list[dict[str, Any]]] = mined.setdefault("kernels", {})
    seen = {k["query"] for ks in kernels.values() for k in ks}
    grammar_fired = set(mined.get("fires", {}))
    stats = {"files": 0, "queries": 0, "probed": 0, "new_rules": 0}
    suite_fires: dict[str, int] = {}
    for f in seed_files:
        stmts = [x.strip() for x in Path(f).read_text(encoding="utf-8", errors="replace").split(";\n")]
        stmts = [x for x in (re.sub(r"^--[^\n]*\n", "", x).strip() for x in stmts) if x]
        stats["files"] += 1
        for setup, q in _split(stmts):
            if stats["queries"] >= max_queries:
                break
            stats["queries"] += 1
            fired = lab.fired(setup, q)
            if not fired:
                continue
            stats["probed"] += 1
            for r in fired:
                suite_fires[r] = suite_fires.get(r, 0) + 1
            for r in sorted(fired):
                if len(kernels.get(r, [])) >= per_rule:
                    continue

                def interesting(toks: list[Any], r: str = r, setup: list[str] = setup) -> bool:
                    sql = render(toks)
                    return r in (lab.fired(setup, sql, [r]) or ()) and lab.rows(setup, sql) is not None

                toks = lex(q)
                if not interesting(toks):
                    continue
                red = render(TokenReducer(interesting, budget=budget, time_budget_s=120).reduce(toks))
                if _one_line(red) in seen:
                    continue
                seen.add(_one_line(red))
                kernels.setdefault(r, []).append({
                    "rule": r, "setup": [_one_line(s) for s in setup], "query": _one_line(red),
                    "tokens": len(lex(red)), "tokens_before": len(toks), "fired": sorted(lab.fired(setup, red) or {r}),
                    "reduced_on_tree": False, "source": "suite", "test_file": str(f)})
                if r not in grammar_fired:
                    stats["new_rules"] += 1
                log(f"suite kernel {r}{'' if r in grammar_fired else ' (never fired by the grammar)'}: "
                    f"{len(toks)} -> {kernels[r][-1]['tokens']} tokens: {kernels[r][-1]['query'][:100]}")
    mined["suite_fires"] = dict(sorted(suite_fires.items()))
    mined["suite_stats"] = stats
    mined["never_fired_after_suite"] = sorted(set(mined.get("rules", lab.rules)) - grammar_fired - set(suite_fires))
    return mined


def transfer(mined: dict[str, Any], config: str, name: str | None = None,
             mem_limit_gb: float | None = 3.0) -> dict[str, Any]:
    """Kernel transfer: run the kernels mined on one engine on another engine (``config``) and
    record which of its rules fire. The result maps each source rule to the target rules its
    kernels trigger, i.e. a measured correspondence between two optimizers' rules, and lists the
    target rules reached only through transferred kernels. A kernel whose SQL the target rejects
    counts as not transferable (dialect gap)."""
    cap_memory(mem_limit_gb)
    lab = Lab(config, name)
    out: dict[str, Any] = {"source": mined.get("engine"), "target": lab.engine, "target_version": lab.version,
                           "kernels": 0, "ran": 0, "fired_any": 0, "errors": {}, "mapping": {}}
    reached: set[str] = set()
    for rule, ks in sorted(mined.get("kernels", {}).items()):
        for k in ks:
            out["kernels"] += 1
            if lab.rows(k.get("setup", []), k["query"]) is None:
                err = (lab.last_error or ("?", ""))[0]
                out["errors"][err] = out["errors"].get(err, 0) + 1
                continue
            out["ran"] += 1
            fired = lab.fired(k.get("setup", []), k["query"]) or set()
            if fired:
                out["fired_any"] += 1
            reached |= fired
            m = out["mapping"].setdefault(rule, {})
            for r in fired:
                m[r] = m.get(r, 0) + 1
    out["target_rules_reached"] = sorted(reached)
    out["target_rules"] = lab.rules
    return out


# name -> (composition, expected), both over derived tables (A) AS ka and (B) AS kb
TEMPLATES: dict[str, tuple[str, str]] = {
    "product": ("SELECT count(*) FROM ({A}) AS ka CROSS JOIN ({B}) AS kb",
                "SELECT (SELECT count(*) FROM ({A}) AS ka) * (SELECT count(*) FROM ({B}) AS kb)"),
    "union": ("SELECT count(*) FROM (SELECT 1 AS k FROM ({A}) AS ka UNION ALL SELECT 2 AS k FROM ({B}) AS kb) AS u",
              "SELECT (SELECT count(*) FROM ({A}) AS ka) + (SELECT count(*) FROM ({B}) AS kb)"),
    "exists": ("SELECT count(*) FROM ({A}) AS ka WHERE EXISTS (SELECT 1 FROM ({B}) AS kb)",
               "SELECT CASE WHEN (SELECT count(*) FROM ({B}) AS kb) > 0 THEN (SELECT count(*) FROM ({A}) AS ka) "
               "ELSE 0 END"),
    "scalar_filter": ("SELECT count(*) FROM ({A}) AS ka WHERE (SELECT count(*) FROM ({B}) AS kb) >= 0",
                      "SELECT count(*) FROM ({A}) AS ka"),
    "cte_twice": ("WITH ka AS ({A}), kb AS ({B}) SELECT (SELECT count(*) FROM ka) + (SELECT count(*) FROM kb) "
                  "+ (SELECT count(*) FROM ka)",
                  "SELECT 2 * (SELECT count(*) FROM ({A}) AS ka) + (SELECT count(*) FROM ({B}) AS kb)"),
    "not_exists": ("SELECT count(*) FROM ({A}) AS ka WHERE NOT EXISTS (SELECT 1 FROM ({B}) AS kb)",
                   "SELECT CASE WHEN (SELECT count(*) FROM ({B}) AS kb) = 0 THEN (SELECT count(*) FROM ({A}) AS ka) "
                   "ELSE 0 END"),
}


# Identity grafts: a base table "T AS x" of kernel A is replaced by a derived table over T whose
# filter is always true but contains kernel B. The result of A must not change (full row multiset),
# while A's rule now has to work across B.
GRAFTS: dict[str, str] = {
    "graft_scalar": "(SELECT * FROM {T} WHERE (SELECT count(*) FROM ({B}) AS kb) >= 0) AS {X}",
    "graft_exists": "(SELECT * FROM {T} WHERE EXISTS (SELECT 1 FROM ({B}) AS kb) "
                    "OR NOT EXISTS (SELECT 1 FROM ({B}) AS kb)) AS {X}",
    "graft_union": "(SELECT * FROM {T} UNION ALL SELECT * FROM {T} WHERE (SELECT count(*) FROM ({B}) AS kb) < 0) "
                   "AS {X}",
}
_TABLE_REF = re.compile(r"\b(FROM|JOIN)\s+\(*\s*([A-Za-z_]\w*)\s+AS\s+(a\d+)\b")


def graft(a: str, b: str, kind: str, rng: random.Random) -> str | None:
    """Kernel ``a`` with one of its base-table references wrapped around kernel ``b``."""
    refs = [m for m in _TABLE_REF.finditer(a) if m.group(2).upper() not in ("SELECT", "LATERAL", "UNNEST")]
    if not refs:
        return None
    m = rng.choice(refs)
    return a[:m.start(2)] + GRAFTS[kind].format(T=m.group(2), X=m.group(3), B=b) + a[m.end(3):]


def compose(config: str, mined: dict[str, Any], out_dir: str | Path, per_pair: int = 2, seed: int = 1,
            name: str | None = None, log: Callable[[str], None] = print) -> dict[str, Any]:
    """Compose kernels of different rules; write seed files; report pair coverage and violations."""
    lab = Lab(config, name)
    rng = random.Random(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rules = sorted(mined["kernels"])
    stats: dict[str, Any] = {"pairs_tried": 0, "seeds": 0, "invalid": 0, "pairs_cofired": 0, "violations": [],
                             "errors": {}}
    cofired: set[tuple[str, str]] = set()
    names = list(TEMPLATES)
    for r in rules:                                      # every kernel alone (rule-ablation through plan variants)
        for j, k in enumerate(mined["kernels"][r]):
            (out / f"kernel_{_safe(r)}_{j}.sql").write_text(
                f"-- rule kernel: {r} ({mined['engine']})\n" + "".join(s + ";\n" for s in k["setup"])
                + k["query"] + ";\n", encoding="utf-8")
    for i, ra in enumerate(rules):
        for rb in rules[i + 1:]:
            ka, kb = rng.choice(mined["kernels"][ra]), rng.choice(mined["kernels"][rb])
            if ka["setup"] and kb["setup"]:
                continue                                  # two private schemas may clash; keep it simple
            setup = ka["setup"] or kb["setup"]
            stats["pairs_tried"] += 1
            for t in rng.sample(names, min(per_pair, len(names))) + [rng.choice(list(GRAFTS))]:
                a, b = (ka, kb) if rng.random() < 0.5 else (kb, ka)
                if t in GRAFTS:
                    comp, want = graft(a["query"], b["query"], t, rng), a["query"]
                    if comp is None:
                        continue
                else:
                    comp = TEMPLATES[t][0].format(A=a["query"], B=b["query"])
                    want = TEMPLATES[t][1].format(A=a["query"], B=b["query"])
                got = lab.rows(setup, comp)
                err = lab.last_error
                exp = lab.rows(setup, want)
                if got is None or exp is None:
                    stats["invalid"] += 1
                    kind = (err or lab.last_error or ("?", ""))[0]
                    stats["errors"][kind] = stats["errors"].get(kind, 0) + 1
                    if got is None and err and err[0] in ("InternalError", "PanicException"):
                        # both parts run on their own, the composition breaks the engine
                        stats["violations"].append({"rules": [ra, rb], "template": t, "setup": setup, "query": comp,
                                                    "error": list(err)})
                        log(f"INTERNAL {t} [{ra} x {rb}]: {err[1][:120]}")
                        (out / f"pair_{_safe(ra)}__{_safe(rb)}_{t}.sql").write_text(
                            f"-- composition of rule kernels {ra} x {rb} ({mined['engine']}), template {t}\n"
                            + "".join(s + ";\n" for s in setup) + comp + ";\n", encoding="utf-8")
                    continue
                f = lab.fired(setup, comp) or set()
                if ra in f and rb in f:
                    cofired.add((ra, rb))
                if got != exp:
                    stats["violations"].append({"rules": [ra, rb], "template": t, "setup": setup, "query": comp,
                                                "expected_sql": want, "got": got[:3], "expected": exp[:3]})
                    log(f"VIOLATION {t} [{ra} x {rb}]: {got[:1]} != {exp[:1]}: {comp[:160]}")
                (out / f"pair_{_safe(ra)}__{_safe(rb)}_{t}.sql").write_text(
                    f"-- composition of rule kernels {ra} x {rb} ({mined['engine']}), template {t}\n"
                    + "".join(s + ";\n" for s in setup) + comp + ";\n" + f"-- pgfuzz:check kernel:{t} {want}\n",
                    encoding="utf-8")
                stats["seeds"] += 1
    stats["pairs_cofired"] = len(cofired)
    stats["cofired"] = sorted(map(list, cofired))
    return stats


def _safe(rule: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", rule).strip("_")


def save(mined: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(mined, indent=1), encoding="utf-8")
