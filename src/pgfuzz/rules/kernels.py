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
            for s in setup:
                d.execute(s, False, 0)
            return fn()
        except BaseException as e:           # engine errors of every kind: this probe just says "no"
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            self.last_error = (str(d.error_name(e) or type(e).__name__), str(e)[:300])
            return None
        finally:
            try:
                d.reset_variant()
                d.end()
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
         log: Callable[[str], None] = print) -> dict[str, Any]:
    """Generate ``n`` test cases; keep up to ``per_rule`` kernels for every rule that fires."""
    from pgfuzz.triage.tree_reduce import TreeReducer, load_trees, size

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
