"""Learned semantic normalizers for cross-engine differential testing (task C4).

Two correct engines disagree on many results for reasons that are not bugs: number formatting,
booleans as 1/0, integer division, function semantics. Writing those rules by hand per engine pair
does not scale and is where false positives come from. Here they are inferred by *probing*:

1. run the same grammar-generated test cases on both engines (through their drivers, in process);
2. collect the query results that differ (as multisets of rendered rows);
3. **normalizers**: greedily pick, from a library of value normalizers
   (:data:`pgfuzz.eval.normalize.NORMALIZERS`), the one that makes the most of the remaining
   disagreements equal, until none explains at least ``min_support`` of them;
4. **guards**: for the disagreements no normalizer explains, find query features (function
   names, operators, casts, keywords) whose presence predicts a disagreement (support and
   rate thresholds), greedily, and skip comparisons of statements with such a feature;
5. validate on held-out test cases: disagreement rate before / after normalizers / after guards,
   and the share of compared statements the guards skip.

The result is data (YAML) that :class:`pgfuzz.reference.xversion_executor.CrossVersionExecutor`
loads with ``learned: <file>``.
"""

from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from pgfuzz.eval.normalize import NORMALIZERS

_FN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_CAST = re.compile(r"::\s*([A-Za-z_][A-Za-z0-9_]*(?:\[\])?)|\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\s*\)", re.I)
_OPS = {"/": r"[^/*]/(?![/*])", "%": r"%(?!')", "||": r"\|\|", "<<": r"<<", ">>": r">>", "&": r"[^&]&[^&]",
        "|": r"[^|]\|[^|]", "^": r"\^", "~": r"~", "->": r"->", "->>": r"->>"}
_KEYWORDS = ("ORDER BY", "LIMIT", "DISTINCT", "GROUP BY", "HAVING", "UNION", "INTERSECT", "EXCEPT", "OVER",
             "FILTER", "CASE", "BETWEEN", "LIKE", "IN (", "EXISTS", "JOIN", "LEFT JOIN", "FULL JOIN", "NULLS")
_NOT_FUNCTIONS = {"IN", "AS", "AND", "OR", "NOT", "VALUES", "OVER", "FILTER", "EXISTS", "ON", "USING", "SELECT",
                  "FROM", "WHERE", "ANY", "ALL", "SOME", "CAST", "ROW", "ARRAY", "THEN", "ELSE", "WHEN", "BY"}


def query_features(sql: str) -> frozenset[str]:
    """Coarse features a guard can name: ``fn:<name>``, ``op:<op>``, ``cast:<type>``, ``kw:<keyword>``."""
    out = set()
    text = re.sub(r"'(?:[^']|'')*'", "''", sql)          # string literals cannot hold features
    for m in _FN.finditer(text):
        name = m.group(1).upper()
        if name not in _NOT_FUNCTIONS:
            out.add(f"fn:{name}")
    for m in _CAST.finditer(text):
        t = (m.group(1) or m.group(2) or "").lower()
        if t:
            out.add(f"cast:{t}")
    for op, pat in _OPS.items():
        if re.search(pat, text):
            out.add(f"op:{op}")
    up = " ".join(text.upper().split())
    for kw in _KEYWORDS:
        if kw in up:
            out.add(f"kw:{kw.strip(' (')}")
    return frozenset(out)


@dataclass
class Record:
    sql: str
    a: list[tuple] | None      # rendered rows (None: error)
    b: list[tuple] | None
    features: frozenset[str] = frozenset()

    @property
    def comparable(self) -> bool:
        return self.a is not None and self.b is not None


def _apply(fs: list[Callable[[str | None], str | None]], rows: list[tuple]) -> list[tuple]:
    out = []
    for r in rows:
        vals = []
        for v in r:
            for f in fs:
                v = f(v)
            vals.append(v)
        out.append(tuple(vals))
    return out


def _same(fs: list[Callable], a: list[tuple], b: list[tuple]) -> bool:
    key = lambda r: tuple("\x00" if v is None else str(v) for v in r)   # noqa: E731
    return sorted(_apply(fs, a), key=key) == sorted(_apply(fs, b), key=key)


@dataclass
class Learned:
    normalize: list[str] = field(default_factory=list)
    guards: list[str] = field(default_factory=list)          # feature names
    stats: dict[str, Any] = field(default_factory=dict)

    def guarded(self, features: Iterable[str]) -> bool:
        return bool(set(features) & set(self.guards))

    def to_dict(self) -> dict[str, Any]:
        return {"normalize": list(self.normalize), "guards": list(self.guards), "stats": self.stats}


def infer(records: list[Record], library: dict[str, Callable] | None = None, min_support: int = 2,
          guard_min_support: int = 3, guard_min_rate: float = 0.5, max_guards: int = 20) -> Learned:
    """Normalizers and guards from probe records (see the module docstring)."""
    lib = dict(library or NORMALIZERS)
    comp = [r for r in records if r.comparable]
    chosen: list[str] = []
    open_ = [r for r in comp if not _same([], r.a, r.b)]   # type: ignore[arg-type]
    explained: dict[str, int] = {}
    while open_:
        best, best_n = None, 0
        for name, f in lib.items():
            if name in chosen:
                continue
            fs = [lib[n] for n in chosen] + [f]
            n = sum(_same(fs, r.a, r.b) for r in open_)   # type: ignore[arg-type]
            if n > best_n:
                best, best_n = name, n
        if best is None or best_n < min_support:
            break
        chosen.append(best)
        explained[best] = best_n
        fs = [lib[n] for n in chosen]
        open_ = [r for r in open_ if not _same(fs, r.a, r.b)]   # type: ignore[arg-type]
    # guards: features over-represented in the residual disagreements
    feat_all: Counter[str] = Counter(f for r in comp for f in r.features)
    guards: list[str] = []
    residual = list(open_)
    while residual and len(guards) < max_guards:
        feat_bad: Counter[str] = Counter(f for r in residual for f in r.features)
        cands = [(feat_bad[f], feat_bad[f] / feat_all[f], f) for f in feat_bad
                 if feat_bad[f] >= guard_min_support and feat_bad[f] / feat_all[f] >= guard_min_rate]
        if not cands:
            break
        cands.sort(key=lambda c: (c[0] * c[1], c[0]), reverse=True)
        g = cands[0][2]
        guards.append(g)
        residual = [r for r in residual if g not in r.features]
    stats = {"records": len(records), "comparable": len(comp),
             "disagree": sum(not _same([], r.a, r.b) for r in comp),   # type: ignore[arg-type]
             "explained_by": explained, "residual_after_normalize": len(open_),
             "residual_after_guards": len(residual),
             "guarded_share": round(sum(bool(set(r.features) & set(guards)) for r in comp) / max(1, len(comp)), 4)}
    return Learned(chosen, guards, stats)


def evaluate(learned: Learned, records: list[Record], library: dict[str, Callable] | None = None) -> dict[str, Any]:
    """Disagreement rates of held-out records before and after the learned rules."""
    lib = dict(library or NORMALIZERS)
    fs = [lib[n] for n in learned.normalize]
    comp = [r for r in records if r.comparable]
    before = sum(not _same([], r.a, r.b) for r in comp)   # type: ignore[arg-type]
    after_norm = [r for r in comp if not _same(fs, r.a, r.b)]   # type: ignore[arg-type]
    kept = [r for r in comp if not learned.guarded(r.features)]
    after_guard = [r for r in after_norm if not learned.guarded(r.features)]
    n = max(1, len(comp))
    return {"comparable": len(comp), "disagree_rate_before": round(before / n, 4),
            "disagree_rate_after_normalize": round(len(after_norm) / n, 4),
            "disagree_rate_after_guards": round(len(after_guard) / max(1, len(kept)), 4),
            "guarded_share": round(1 - len(kept) / n, 4), "residual": len(after_guard),
            "residual_examples": [r.sql[:300] for r in after_guard[:10]]}


# ------------------------------------------------------------------ probing

def _rows(driver: Any, sql: str, max_rows: int) -> list[tuple] | None:
    from pgfuzz.targets.base import _render

    try:
        rows, _ = driver.execute(sql, True, max_rows)
    except Exception:
        return None
    if rows is None:
        return None
    return [tuple(_render(v) for v in r) for r in rows]


def probe(driver_a: Any, driver_b: Any, testcases: Iterable[list[str]], max_rows: int = 200) -> list[Record]:
    """Run each test case's statements on both drivers (one transaction per test case) and
    record the results of the deterministic queries."""
    from pgfuzz.eval.differential import xversion_eligible

    out: list[Record] = []
    for stmts in testcases:
        for d in (driver_a, driver_b):
            try:
                d.begin()
            except Exception:
                pass
        for sql in stmts:
            q = sql.lstrip()[:6].upper() in ("SELECT", "VALUES") or sql.lstrip()[:4].upper() == "WITH"
            if not q:
                for d in (driver_a, driver_b):
                    try:
                        d.execute(sql, False, 0)
                    except Exception:
                        pass
                continue
            a, b = _rows(driver_a, sql, max_rows), _rows(driver_b, sql, max_rows)
            if xversion_eligible(sql):
                out.append(Record(sql, a, b, query_features(sql)))
        for d in (driver_a, driver_b):
            try:
                d.end()
            except Exception:
                pass
    return out


def split(records: list[Record], seed: int = 0, train: float = 0.5) -> tuple[list[Record], list[Record]]:
    rs = list(records)
    random.Random(seed).shuffle(rs)
    k = int(len(rs) * train)
    return rs[:k], rs[k:]


def _run_case(ex: Any, stmts: list[str]) -> list[list[tuple] | None]:
    """Results of ``stmts`` on a started WorkerExecutor, one test case in one transaction
    (statement timeouts and crash isolation come from the worker)."""
    out: list[list[tuple] | None] = []
    if not ex._alive():
        ex._spawn()
    ex._op("begin")
    done: list[str] = []
    for sql in stmts:
        r = ex._exec(sql)
        if r["status"] == "connection_lost":
            ex._spawn()
            out += [None] * (len(stmts) - len(out))
            return out
        if r["status"] != "ok":
            out.append(None)
            ex._recover(done, r["status"] == "timeout")
            continue
        done.append(sql)
        out.append([tuple(x) for x in r["rows"]] if r["rows"] is not None else None)
    if ex._alive():
        ex._op("end")
    else:
        ex._spawn()
    return out


def probe_executors(ex_a: Any, ex_b: Any, testcases: Iterable[list[str]]) -> list[Record]:
    from pgfuzz.eval.differential import xversion_eligible

    out: list[Record] = []
    for stmts in testcases:
        ra, rb = _run_case(ex_a, stmts), _run_case(ex_b, stmts)
        for sql, a, b in zip(stmts, ra, rb):
            s = sql.lstrip().upper()
            if (s.startswith("SELECT") or s.startswith("VALUES") or s.startswith("WITH")) and xversion_eligible(sql):
                out.append(Record(sql, a, b, query_features(sql)))
    return out


def save_records(records: list[Record], path: str) -> None:
    import json

    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps({"sql": r.sql, "a": r.a, "b": r.b, "features": sorted(r.features)}) + "\n")


def load_records(path: str) -> list[Record]:
    import json

    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            a = [tuple(x) for x in d["a"]] if d["a"] is not None else None
            b = [tuple(x) for x in d["b"]] if d["b"] is not None else None
            out.append(Record(d["sql"], a, b, frozenset(d["features"])))
    return out


def learn_from_config(config: str, name: str | None, n: int, seed: int = 1,
                      records_out: str | None = None, depth: int | None = 5,
                      guard_min_rate: float = 0.5) -> tuple[Learned, dict[str, Any]]:
    """Generate ``n`` test cases with the config's generator and probe its cross-engine executor
    pair (``executor.params.test`` / ``reference``) without any normalizer; learn on half the
    test cases and evaluate on the other half."""
    import tempfile
    from pathlib import Path

    from pgfuzz.core.interfaces import Executor, Generator, GeneratorContext
    from pgfuzz.core.plugins import instantiate
    from pgfuzz.runner import load_config

    cfg = load_config(config)
    fc = next((c for c in cfg.configs if c.name == name), None) if name else cfg.configs[0]
    if fc is None:
        raise SystemExit(f"no config named {name!r}")
    params = dict(fc.generator.render(**cfg.substitutions(fc.name, 0, 0)))
    params["mm_prob"] = 0.0
    if depth:            # small probes: a disagreement can be attributed to few features
        params["max_depth"], params["soft_depth"] = depth, max(2, depth - 2)
    gen = instantiate(fc.generator.plugin, Generator, params)
    gen.setup(GeneratorContext(seed, random.Random(seed), Path(tempfile.mkdtemp(prefix="pgfuzz-learn-"))))
    ex_params = cfg.executor.render(**cfg.substitutions(fc.name, 0, 0))
    sides = []
    test_spec = dict(ex_params["test"])
    for key in ("test", "reference"):
        spec = dict(ex_params[key])
        for k in ("setup_sql", "reset_sql", "session_sql", "statement_timeout_ms"):   # as CrossVersionExecutor
            if k in test_spec and k not in spec:
                spec[k] = test_spec[k]
        plugin = spec.pop("plugin")
        for k in ("normalize", "metamorphic", "differential", "rule_feedback"):
            spec.pop(k, None)
        sides.append(instantiate(plugin, Executor, spec))
    cases = []
    for _ in range(n):
        tc = gen.next_testcase()
        if tc is None:
            break
        cases.append(list(tc.statements))
    for ex in sides:
        ex.start()
    try:
        records = probe_executors(sides[0], sides[1], cases)
    finally:
        for ex in sides:
            ex.stop()
    if records_out:
        save_records(records, records_out)
    half = len(cases) // 2
    train_sql = {s for c in cases[:half] for s in c}
    train = [r for r in records if r.sql in train_sql]
    test = [r for r in records if r.sql not in train_sql]
    learned = infer(train, guard_min_rate=guard_min_rate)
    report = {"train": learned.stats, "held_out": evaluate(learned, test),
              "pair": [sides[0].describe().get("version"), sides[1].describe().get("version")]}
    learned.stats = report
    return learned, report
