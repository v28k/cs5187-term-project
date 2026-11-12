"""Command line: ``python -m pgfuzz <command> ...`` (run from ``src/``)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any


def _setup_logging(verbose: int) -> None:
    level = logging.DEBUG if verbose > 1 else logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")


def cmd_run(a: argparse.Namespace) -> int:
    from pgfuzz.report import build_report
    from pgfuzz.runner import load_config, run_experiment
    from pgfuzz.runner.experiment import plan

    cfg = load_config(a.config)
    only = a.only.split(",") if a.only else None
    p = plan(cfg, only, a.trials, a.fresh)
    print(f"experiment {cfg.experiment}: {len(p.todo)} trial(s) to run, {len(p.done)} already finished")
    print(f"  output:  {cfg.experiment_dir}")
    print(f"  budget:  {cfg.budget.describe()} per trial")
    for fc in cfg.enabled_configs(only):
        print(f"  config:  {fc.name:<14} {fc.generator.plugin}")
    if a.dry_run:
        for fc, t in p.todo:
            print(f"  would run {fc.name} trial {t} (seed {cfg.trial_seed(t)})")
        return 0
    from pgfuzz.core.procs import lead_process_group

    lead_process_group()  # Ctrl-C / kill stops every worker, including engine workers
    try:
        run_experiment(cfg, jobs=a.jobs, only=only, trials=a.trials, fresh=a.fresh)
    except (KeyboardInterrupt, SystemExit):
        print("\ninterrupted; finished trials are kept, re-run the same command to resume", file=sys.stderr)
        return 130
    if not a.no_report:
        out = build_report(cfg.experiment_dir, plots=not a.no_plots)
        print(f"report: {out / 'report.md'}")
    return 0


def cmd_report(a: argparse.Namespace) -> int:
    from pgfuzz.report import build_report

    out = build_report(a.experiment_dir, a.out, plots=not a.no_plots)
    print(f"report: {out / 'report.md'}")
    return 0


def cmd_learn_normalizers(a: argparse.Namespace) -> int:
    """Probe a cross-engine pair, learn normalizers and guards, report held-out precision."""
    import yaml

    from pgfuzz.normalizers.infer import learn_from_config

    learned, report = learn_from_config(a.config, a.name, a.n, a.seed, a.records, a.depth or None, a.guard_rate)
    print(json.dumps({"normalize": learned.normalize, "guards": learned.guards, **report}, indent=1, default=str))
    if a.out:
        Path(a.out).write_text(yaml.safe_dump(learned.to_dict(), sort_keys=False), encoding="utf-8")
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    from pgfuzz.runlog import validate_run

    root = Path(a.path)
    trials = [root] if (root / "manifest.json").exists() else sorted(p.parent for p in root.glob("*/trial-*/manifest.json"))
    if not trials:
        print(f"no trial directories under {root}", file=sys.stderr)
        return 2
    bad = 0
    for t in trials:
        errs = validate_run(t)
        if errs:
            bad += 1
            print(f"INVALID {t}")
            for e in errs:
                print(f"  {e}")
        else:
            print(f"ok      {t}")
    return 1 if bad else 0


def _executor_from(config: str, name: str | None):
    from pgfuzz.core.interfaces import Executor
    from pgfuzz.core.plugins import instantiate
    from pgfuzz.runner import load_config

    cfg = load_config(config)
    spec = cfg.executor
    if name:
        fc = next((c for c in cfg.configs if c.name == name), None)
        if fc is None:
            raise SystemExit(f"no config named {name!r}")
        spec = fc.executor or spec
    return instantiate(spec.plugin, Executor, spec.render(**cfg.substitutions(name or "", 0, 0)))


def cmd_selftest(a: argparse.Namespace) -> int:
    from pgfuzz.runner.selftest import run_selftest

    results = run_selftest(_executor_from(a.config, a.name))
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        expect = [e.value if e else "skipped" for e in r.check.expect]
        print(f"{status}  {r.check.name:<12} {r.check.why}")
        if not r.passed:
            print(f"      expected {expect}, got {r.got}")
            if r.error:
                print(f"      {r.error}")
    failed = sum(not r.passed for r in results)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


def cmd_replay(a: argparse.Namespace) -> int:
    from pgfuzz.core.types import TestCase
    from pgfuzz.grammar.generator import parse_seed
    from pgfuzz.eval import oracle, signature
    from pgfuzz.eval.known_bugs import KnownBugCatalog
    from pgfuzz.runner import load_config

    cfg = load_config(a.config)
    catalog = KnownBugCatalog.load(cfg.known_bugs)
    ex = _executor_from(a.config, a.name)
    ex.start()
    found = 0
    try:
        for i, f in enumerate(a.files):
            stmts, checks = parse_seed(Path(f).read_text(encoding="utf-8"))
            tc = TestCase(stmts, origin="replay", id=i, meta={"checks": checks} if checks else {})
            for _ in range(a.repeat):
                res = ex.execute(tc)
                cls = oracle.classify(res)
                rec = {"file": f, "outcome": cls.outcome.value, "culprit": cls.culprit, "sqlstate": cls.sqlstate,
                       "message": cls.message}
                if cls.is_bug_candidate:
                    found += 1
                    sig = signature.compute(cls, tc)
                    rec.update(signature=sig.id, strength=sig.strength, known_bugs=catalog.match(cls, tc),
                               details={k: v for k, v in cls.details.items() if k != "backtrace"})
                print(json.dumps(rec))
    finally:
        ex.stop()
    return 0 if found or not a.expect_bug else 1


def cmd_sample(a: argparse.Namespace) -> int:
    """Print generated test cases, or (--execute) run them and summarise the
    generator's validity statistics: the inner loop of grammar development."""
    import random
    import tempfile
    import time

    from pgfuzz.core.interfaces import Feedback, Generator, GeneratorContext
    from pgfuzz.core.plugins import instantiate
    from pgfuzz.eval import oracle
    from pgfuzz.runner import load_config

    cfg = load_config(a.config)
    fc = next((c for c in cfg.configs if c.name == a.name), None) if a.name else cfg.configs[0]
    if fc is None:
        raise SystemExit(f"no config named {a.name!r}")
    gen = instantiate(fc.generator.plugin, Generator, fc.generator.render(**cfg.substitutions(fc.name, 0, 0)))
    gen.setup(GeneratorContext(a.seed, random.Random(a.seed), Path(tempfile.mkdtemp(prefix="pgfuzz-sample-"))))
    if not a.execute:
        for i in range(a.n):
            tc = gen.next_testcase()
            if tc is None:
                break
            print(f"-- testcase {i} ({tc.meta.get('op', '')})")
            for s in tc.statements:
                print(s + ";")
        return 0
    ex = _executor_from(a.config, fc.name)
    out = Path(a.out) if a.out else None
    ex.start()
    t0 = time.monotonic()
    bugs = 0
    import collections
    import re as _re

    n_ok = n_err = q_ok = q_all = 0
    errs: collections.Counter[str] = collections.Counter()
    examples: dict[str, tuple[str, str]] = {}
    try:
        for i in range(a.n):
            tc = gen.next_testcase()
            if tc is None:
                break
            tc.id = i
            res = ex.execute(tc)
            k = int(tc.meta.get("synth", 0))     # synthesized rows (C3) are not generated statements
            for sql, r in zip(tc.statements[k:], res.statements[k:]):
                is_q = sql.lstrip()[:6].upper() in ("SELECT", "WITH  ", "VALUES") or sql.lstrip()[:4].upper() == "WITH"
                q_all += is_q
                if r.status.value == "ok":
                    n_ok += 1
                    q_ok += is_q
                elif r.status.value == "error":
                    n_err += 1
                    m = _re.sub(r'"[^"]*"|\'[^\']*\'|\d+', "?", (r.message or "").split("\n")[0])[:110]
                    errs[m] += 1
                    examples.setdefault(m, (sql[:20000], (r.message or "")[:300]))
            cls = oracle.classify(res)
            if cls.is_bug_candidate and hasattr(gen, "failure_meta"):
                tc.meta.update(gen.failure_meta(tc) or {})
            gen.feedback(Feedback(tc, res, cls.outcome, cls.statement_outcomes, frozenset(), False))
            if cls.is_bug_candidate:
                bugs += 1
                print(f"BUG CANDIDATE #{i}: {cls.outcome.value} {cls.sqlstate or ''} {cls.message or ''}"[:300])
                if out:
                    out.mkdir(parents=True, exist_ok=True)
                    (out / f"tc{i}.sql").write_text(";\n".join(tc.statements) + ";\n", encoding="utf-8")
                    (out / f"tc{i}.json").write_text(json.dumps({
                        "outcome": cls.outcome.value, "culprit": cls.culprit, "sqlstate": cls.sqlstate,
                        "message": cls.message, "details": cls.details, "meta": tc.meta,
                        "statements": [r.to_dict() for r in res.statements]}, indent=1, default=str), encoding="utf-8")
    finally:
        ex.stop()
    stats = getattr(gen, "stats", lambda: {})()
    stats["elapsed_s"] = round(time.monotonic() - t0, 1)
    stats["bug_candidates"] = bugs
    stats["executor"] = dict(getattr(ex, "diff_stats", {}) or {})
    stats["validity"] = {"statements_ok": n_ok, "statements_error": n_err,
                         "statement_valid_rate": round(n_ok / max(1, n_ok + n_err), 4),
                         "queries": q_all, "query_valid_rate": round(q_ok / max(1, q_all), 4)}
    stats["top_errors"] = errs.most_common(a.errors)
    if a.examples:
        stats["error_examples"] = {m: examples[m] for m, _ in errs.most_common(a.errors)}
    if a.quiet_stats:
        stats = {k: stats[k] for k in ("validity", "top_errors", "bug_candidates", "elapsed_s", "error_examples")
                 if k in stats}
    if a.mine_overlay:
        from pgfuzz.grammar.miner import mine, render_overlay

        found = mine(gen, a.mine_min_uses, a.mine_max_ok)
        Path(a.mine_overlay).write_text(render_overlay(found, Path(a.config).stem), encoding="utf-8")
        stats["mined_overlay"] = {"path": a.mine_overlay, "directives": sum(1 for d in found if d["key"]),
                                  "alternatives": len(found)}
    print(json.dumps(stats, indent=1))
    return 0


def cmd_triage(a: argparse.Namespace) -> int:
    from pgfuzz.triage.triage import load_candidate, triage, verdict_template

    paths: list[Path] = []
    for f in a.candidates:
        p = Path(f)
        if p.is_dir() and not (p / "failure.json").exists():   # an experiment / trial directory
            paths += sorted(q.parent for q in p.glob("**/failures/*/failure.json"))
            paths += sorted(q.with_suffix(".sql") for q in p.glob("tc*.json"))
        else:
            paths.append(p)
    if not paths:
        print("no candidates found", file=sys.stderr)
        return 2
    ex = _executor_from(a.config, a.name)
    ref = _executor_from(a.reference, None) if a.reference else None
    out = Path(a.out)
    results = []
    ex.start()
    if ref is not None:
        ref.start()
    try:
        seen: set[str] = set()
        gens: dict[str, Any] = {}
        for p in paths:
            cand = load_candidate(p)
            if cand.signature in seen:
                continue
            seen.add(cand.signature)
            results.append(triage(cand, ex, out, repeat=a.repeat, reduce=not a.no_reduce, reference=ref,
                                  budget=a.budget, tree_gen=None if a.no_tree else _tree_gen(cand.meta, gens)))
    finally:
        ex.stop()
        if ref is not None:
            ref.stop()
    out.mkdir(parents=True, exist_ok=True)
    tmpl = out / "verdicts.template.yaml"
    tmpl.write_text(verdict_template(results), encoding="utf-8")
    print(f"{len(results)} candidate(s) triaged into {out}; verdict template: {tmpl}")
    return 0


def _tree_gen(meta: dict | None, cache: dict):
    """A replay-only GrammarGenerator for the grammar a failure was generated with."""
    import random

    from pgfuzz.core.interfaces import GeneratorContext
    from pgfuzz.grammar.generator import GrammarGenerator

    g = (meta or {}).get("generator")
    if not g or not (meta or {}).get("trees") or not Path(g["grammar"]).exists():
        return None
    key = json.dumps(g, sort_keys=True)
    if key not in cache:
        gen = GrammarGenerator(g["grammar"], g["schema"], extra_grammars=g.get("extra_grammars") or None,
                               mutate_prob=0.0, mm_prob=0.0)
        gen.setup(GeneratorContext(0, random.Random(0), Path(".")))
        cache[key] = gen
    return cache[key]


def cmd_precision(a: argparse.Namespace) -> int:
    from pgfuzz.triage.precision import load_verdicts, precision_table, render_latex, render_markdown

    rows = precision_table(load_verdicts(a.verdicts))
    print(render_latex(rows) if a.latex else render_markdown(rows))
    return 0


def cmd_features(a: argparse.Namespace) -> int:
    from pgfuzz.core.sqlsplit import split_statements
    from pgfuzz.eval.features import FEATURE_IDS, features_of

    seen: set[str] = set()
    for f in a.files:
        for s in split_statements(Path(f).read_text(encoding="utf-8")):
            feats = features_of(s)
            seen |= feats
            if a.each:
                print(f"{' '.join(s.split())[:100]}\n    {', '.join(sorted(feats))}")
    print(f"{len(seen)}/{len(FEATURE_IDS)} catalog features covered")
    if a.missing:
        print("missing: " + ", ".join(f for f in FEATURE_IDS if f not in seen))
    return 0


def cmd_llm(a: argparse.Namespace) -> int:
    from pgfuzz.llm import commits as cm

    if a.llm_cmd == "mine":
        ds = cm.mine(a.repo, a.since, a.until, limit=a.limit, require_test=not a.any)
        if a.exclude:
            ex = [ln.split()[0] for ln in Path(a.exclude).read_text().splitlines() if ln.strip() and not ln.startswith("#")]
            ds = [d for d in ds if not any(d.sha.startswith(x) for x in ex)]
        cm.save(ds, a.out)
        print(f"{len(ds)} commit(s) -> {a.out}")
        for d in ds:
            print(f"  {d.short} {d.date} {d.stats['target_lines']:>4} lines  {d.subject[:70]}")
        return 0
    from pgfuzz.llm.loop import render_markdown, summarize

    if a.llm_cmd == "report":
        s = summarize(a.out)
        print(render_markdown(s) if not a.json else json.dumps(s, indent=1))
        return 0
    from pgfuzz.llm.client import LLMClient
    from pgfuzz.llm.gate import Gate, GateConfig
    from pgfuzz.llm.loop import extend
    from pgfuzz.llm.prompt import system_prompt
    from pgfuzz.runner import load_config

    cfg = load_config(a.config)
    gens = [c for c in cfg.configs if "GrammarGenerator" in c.generator.plugin]
    if not gens:
        raise SystemExit("the config has no grammar arm (needed for grammar and schema paths)")
    gargs = gens[0].generator.render(**cfg.substitutions(gens[0].name, 0, 0))
    ds = cm.load(a.commits)
    if a.only:
        ds = [d for d in ds if any(d.sha.startswith(x) for x in a.only.split(","))]
    ds = ds[:a.limit]
    gc = GateConfig(sample_n=a.sample, coverage_build=a.coverage_build, pg_repo=a.pg_repo, pg_head=a.pg_head)
    ex = _executor_from(a.config, a.name)
    client = LLMClient(a.out, mode=a.mode, model=a.model, effort=a.effort)
    ex.start()
    try:
        res = extend(ds, client, Gate(gargs["grammar"], gargs["schema"], ex, gc),
                     system_prompt(gargs["grammar"], gargs["schema"]), a.out, max_rounds=a.rounds)
    finally:
        ex.stop()
    print(f"{res.done} commit(s) finished, {res.accepted} accepted; ledger: {Path(a.out) / 'ledger.jsonl'}")
    if res.stopped_for:
        print(f"manual mode: answer the prompt in {res.stopped_for}, save the JSON as "
              f"{Path(a.out) / 'responses' / (Path(res.stopped_for).stem + '.json')}, and re-run")
    print(render_markdown(summarize(a.out)))
    return 0


def _executor_at(config: str, worker: int, plain: bool = False):
    """The config's executor pointed at worker ``worker`` (port base_port + worker).

    ``plain``: only the server under test (a cross-version executor's ``test``
    side), oracles off, exact result digests -- for comparing PoC outputs."""
    from pgfuzz.core.interfaces import Executor
    from pgfuzz.core.plugins import instantiate
    from pgfuzz.reference.pg_executor import PostgresExecutor
    from pgfuzz.runner import load_config

    cfg = load_config(config)
    params = cfg.executor.render(**cfg.substitutions("bench", worker, 0))
    if not plain:
        return instantiate(cfg.executor.plugin, Executor, params)
    params = dict(params.get("test", params))
    params.update(digests=True, mask_floats=False, differential=False, metamorphic=False, plan_shapes=False)
    return PostgresExecutor(**params)


def cmd_bench(a: argparse.Namespace) -> int:
    from pgfuzz.bench import reinjected as rb
    from pgfuzz.runner import load_config

    cfg = load_config(a.config)
    bench = rb.load(cfg.known_bugs)
    plain = a.bench_cmd == "verify"
    fixed = _executor_at(a.config, rb.FIXED_WORKER, plain)
    solos = [_executor_at(a.config, bench.solo_worker(i), plain) for i in range(len(bench.bugs))]
    exs = [fixed, *solos]
    injected = None
    if plain:
        injected = _executor_at(a.config, 0, plain)
        exs.append(injected)
    for ex in exs:
        ex.start()
    try:
        out = Path(a.out or cfg.experiment_dir)
        out.mkdir(parents=True, exist_ok=True)
        if a.bench_cmd == "verify":
            rows = rb.verify(bench, fixed, solos, injected)
            (out / "bench_verify.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
            print("| bug | commit | symptom | all injected | evidence |\n|---|---|---|---|---|")
            for r in rows:
                print(f"| {r['id']} | {r['commit'][:8]} | {r['symptom']} | {r.get('injected_symptom')} | "
                      f"{r['evidence'][:90]} |")
            for r in rows:
                if r["fixed_errors"]:
                    print(f"note: {r['id']} raises errors on the fixed server: {'; '.join(r['fixed_errors'])[:200]}")
            print(f"\n{sum(r['symptom'] != 'none' for r in rows)}/{len(rows)} bugs observable; "
                  f"copy the symptoms into {cfg.known_bugs}")
            return 0
        res = rb.attribute(bench, a.experiment_dir, fixed, solos, repeat=a.repeat)
        arms = [c.name for c in cfg.configs if c.enabled] + sorted({r["arm"] for r in res} - {c.name for c in cfg.configs})
        table = rb.detection_table(bench, res, arms, cfg.trials)
        (out / "attribution.json").write_text(json.dumps({"failures": res, "table": table}, indent=1, default=str),
                                              encoding="utf-8")
        print(rb.render_markdown(table, arms))
        print(f"\nnative failures (reproduce on the fixed server): {table['native_failures']}; "
              f"unattributed: {table['unattributed_failures']}")
        return 0
    finally:
        for ex in exs:
            ex.stop()


def cmd_profile(a: argparse.Namespace) -> int:
    from pgfuzz.grammar.dsl import load_grammar
    from pgfuzz.grammar.profile import collect
    from pgfuzz.grammar.schema import load_schema
    from pgfuzz.runner import load_config

    cfg = load_config(a.config)
    gens = [c for c in cfg.configs if "GrammarGenerator" in c.generator.plugin]
    if not gens:
        raise SystemExit("the config has no grammar arm (needed for the schema and types)")
    gp = gens[0].generator.render(**cfg.substitutions(gens[0].name, 0, 0))
    g = load_grammar(gp["grammar"])
    ex = _executor_from(a.config, a.name)
    ex.start()
    try:
        data = collect(ex, load_schema(gp["schema"]), {t: d.sql for t, d in g.types.items()})
    finally:
        ex.stop()
    Path(a.out).write_text(json.dumps(data, indent=1), encoding="utf-8")
    ok = sum("error" not in c for c in data["columns"].values())
    print(f"profiled {ok}/{len(data['columns'])} columns -> {a.out}")
    return 0


def cmd_hunt(a: argparse.Namespace) -> int:
    from pgfuzz.agent.hunt import hunt

    s = hunt(a.configs, a.budget, a.out, jobs=a.jobs, repeat=a.repeat, max_triage=a.max_triage)
    n = sum(len(e["packages"]) for e in s["engines"].values())
    print(f"hunt: {len(s['engines'])} campaigns, {n} packages -> {a.out}/HUNT.md")
    return 0


def cmd_package(a: argparse.Namespace) -> int:
    from pgfuzz.agent.package import make_package

    for t in a.triage_dirs:
        print(make_package(a.engine, t, a.out))
    return 0


def cmd_import_tests(a: argparse.Namespace) -> int:
    from pgfuzz.agent.suites import import_suite

    st = import_suite(a.paths, a.out, max_statements=a.max_statements, max_files=a.max_files)
    print(json.dumps(st))
    return 0


def cmd_ledger(a: argparse.Namespace) -> int:
    from pgfuzz.triage.ledger import build, render

    text = render(build(a.root))
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def cmd_kernels(a: argparse.Namespace) -> int:
    from pgfuzz.rules import kernels as K

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.from_json:
        mined = json.loads(Path(a.from_json).read_text(encoding="utf-8"))
    else:
        mined = K.mine(a.config, n=a.n, seed=a.seed, per_rule=a.per_rule, budget=a.budget, name=a.name)
        K.save(mined, out / "kernels.json")
    st = K.compose(a.config, mined, out / "seeds", per_pair=a.per_pair, seed=a.seed, name=a.name)
    (out / "compose.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
    nk = sum(len(v) for v in mined["kernels"].values())
    print(json.dumps({"engine": mined["engine"], "rules": len(mined["rules"]), "rules_with_kernel": len(mined["kernels"]),
                      "kernels": nk, "never_fired": mined["never_fired"], "pairs_tried": st["pairs_tried"],
                      "pairs_cofired": st["pairs_cofired"], "seeds": st["seeds"], "invalid": st["invalid"],
                      "violations": len(st["violations"]), "out": str(out)}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pgfuzz", description="Evaluation harness for grammar-aware PostgreSQL fuzzing")
    ap.add_argument("-v", "--verbose", action="count", default=1, help="-v info (default), -vv debug")
    ap.add_argument("-q", "--quiet", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="run an experiment (resumes unfinished trials)")
    p.add_argument("config")
    p.add_argument("-j", "--jobs", type=int, default=1, help="parallel trials (each needs its own server: use {worker} in the DSN)")
    p.add_argument("--only", help="comma-separated config names")
    p.add_argument("--trials", type=int, help="override number of trials")
    p.add_argument("--fresh", action="store_true", help="re-run finished trials too")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-report", action="store_true")
    p.add_argument("--no-plots", action="store_true")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("report", help="build tables, statistics and plots for an experiment directory")
    p.add_argument("experiment_dir")
    p.add_argument("--out")
    p.add_argument("--no-plots", action="store_true")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("learn-normalizers", help="infer value normalizers and guards for a cross-engine pair (C4)")
    p.add_argument("config")
    p.add_argument("--name", help="config (arm) whose generator to use (default: the first)")
    p.add_argument("-n", type=int, default=400, help="number of probe test cases")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", help="write the learned rules here (YAML)")
    p.add_argument("--records", help="also save the probe records here (JSON lines)")
    p.add_argument("--depth", type=int, default=5, help="grammar depth of the probes (small probes; 0: config's)")
    p.add_argument("--guard-rate", type=float, default=0.5,
                   help="minimum share of a feature's comparisons that must disagree for it to become a guard")
    p.set_defaults(fn=cmd_learn_normalizers)

    p = sub.add_parser("validate", help="check run logs against the log format")
    p.add_argument("path", help="trial directory or experiment directory")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("selftest", help="acceptance checks for the executor configured in an experiment")
    p.add_argument("config")
    p.add_argument("--name", help="use the executor of this config (if it overrides the default)")
    p.set_defaults(fn=cmd_selftest)

    p = sub.add_parser("replay", help="execute .sql files and print the oracle's verdict")
    p.add_argument("config")
    p.add_argument("files", nargs="+")
    p.add_argument("--name")
    p.add_argument("--repeat", type=int, default=1, help="run each file N times (flakiness check)")
    p.add_argument("--expect-bug", action="store_true", help="exit 1 if no file triggers a bug candidate")
    p.set_defaults(fn=cmd_replay)

    p = sub.add_parser("triage", help="reproduce, reduce and report bug candidates")
    p.add_argument("config", help="experiment config whose executor runs the candidates")
    p.add_argument("candidates", nargs="+",
                   help="failure directories, sample tcN.sql files, or an experiment/trial/sample directory")
    p.add_argument("--name", help="use the executor of this config")
    p.add_argument("--out", default="../results/triage")
    p.add_argument("--repeat", type=int, default=3, help="reproduction attempts before reducing")
    p.add_argument("--budget", type=int, default=400, help="max executions per token reduction")
    p.add_argument("--no-reduce", action="store_true")
    p.add_argument("--no-tree", action="store_true", help="skip grammar-tree reduction (token reduction only)")
    p.add_argument("--reference", help="config whose executor is a release server (shows its rows in the report)")
    p.set_defaults(fn=cmd_triage)

    p = sub.add_parser("precision", help="per-oracle precision from triage verdicts (RQ2)")
    p.add_argument("verdicts", help="triage/verdicts.yaml")
    p.add_argument("--latex", action="store_true")
    p.set_defaults(fn=cmd_precision)

    p = sub.add_parser("features", help="show SQL feature coverage of .sql files")
    p.add_argument("files", nargs="+")
    p.add_argument("--missing", action="store_true", help="list catalog features not covered")
    p.add_argument("--each", action="store_true", help="print the features of every statement")
    p.set_defaults(fn=cmd_features)

    p = sub.add_parser("sample", help="print generated test cases, or run them and show validity statistics")
    p.add_argument("config")
    p.add_argument("--name", help="config (arm) whose generator to use (default: the first)")
    p.add_argument("-n", type=int, default=10, help="number of test cases")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--execute", action="store_true", help="run them on the configured executor")
    p.add_argument("--out", help="directory for bug-candidate test cases")
    p.add_argument("--errors", type=int, default=25, help="how many top error messages to show")
    p.add_argument("--examples", action="store_true", help="show one failing statement per error message")
    p.add_argument("--quiet-stats", action="store_true", help="show only validity, top errors, candidates")
    p.add_argument("--mine-overlay", metavar="PATH", help="(with --execute) write a draft overlay of failing alternatives (A3)")
    p.add_argument("--mine-min-uses", type=int, default=20)
    p.add_argument("--mine-max-ok", type=float, default=0.1)
    p.set_defaults(fn=cmd_sample)

    p = sub.add_parser("llm", help="commit-directed grammar extension (Grammar + LLM arm)")
    lsub = p.add_subparsers(dest="llm_cmd", required=True)
    q = lsub.add_parser("mine", help="digest recent PostgreSQL commits")
    q.add_argument("repo", help="PostgreSQL git checkout")
    q.add_argument("--since", required=True, help="date (YYYY-MM-DD) or ref")
    q.add_argument("--until", default="HEAD")
    q.add_argument("--limit", type=int, default=200)
    q.add_argument("--any", action="store_true", help="also commits that add no regression-test SQL")
    q.add_argument("--exclude", help="file of commit shas to leave out (RQ3: bench/reinjected/commits.txt, "
                                     "so the model never sees the fixes of the re-injected bugs)")
    q.add_argument("--out", default="../results/llm/commits.json")
    q = lsub.add_parser("extend", help="ask for fragments, gate them on the server, repair, keep the accepted")
    q.add_argument("config", help="experiment config (executor + grammar arm)")
    q.add_argument("commits", help="commits.json from 'llm mine'")
    q.add_argument("--name", help="use the executor of this config")
    q.add_argument("--out", default="../results/llm")
    q.add_argument("--mode", choices=["api", "manual"], default="api")
    q.add_argument("--model", default="claude-opus-5-5")
    q.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    q.add_argument("--rounds", type=int, default=3, help="proposal + repair rounds per commit")
    q.add_argument("--limit", type=int, default=30)
    q.add_argument("--only", help="comma-separated commit sha prefixes")
    q.add_argument("--sample", type=int, default=150, help="test cases per gate sample")
    q.add_argument("--coverage-build", help="gcov build dir of the server (enables the diff-coverage check)")
    q.add_argument("--pg-repo", help="git checkout for mapping changed lines to the build's revision")
    q.add_argument("--pg-head", default="HEAD")
    q = lsub.add_parser("report", help="RQ4 summary of a ledger")
    q.add_argument("--out", default="../results/llm")
    q.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_llm)

    p = sub.add_parser("profile", help="data profile of the schema (quantile and boundary literals)")
    p.add_argument("config")
    p.add_argument("--name")
    p.add_argument("--out", default="corpus/profile.json")
    p.set_defaults(fn=cmd_profile)

    p = sub.add_parser("bench", help="RQ3 re-injected bug benchmark (configs/rq3.yaml)")
    bsub = p.add_subparsers(dest="bench_cmd", required=True)
    q = bsub.add_parser("verify", help="run every PoC on the fixed, solo and all-injected servers")
    q.add_argument("config")
    q.add_argument("--out")
    q = bsub.add_parser("attribute", help="attribute a campaign's failures to injected bugs; per-arm table")
    q.add_argument("config")
    q.add_argument("experiment_dir")
    q.add_argument("--repeat", type=int, default=2)
    q.add_argument("--out")
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("hunt", help="autonomous round: campaigns per engine, triage of new failures, package drafts")
    p.add_argument("configs", nargs="+")
    p.add_argument("--budget", type=float, default=3600, help="seconds per campaign")
    p.add_argument("--out", default="results/hunt")
    p.add_argument("-j", "--jobs", type=int, default=2, help="campaigns in parallel")
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--max-triage", type=int, default=20)
    p.set_defaults(fn=cmd_hunt)

    p = sub.add_parser("package", help="filing-package draft (native regression test, report) from triage output")
    p.add_argument("engine", choices=["duckdb", "sqlite", "turso", "datafusion", "postgres"])
    p.add_argument("triage_dirs", nargs="+")
    p.add_argument("--out", default="results/packages")
    p.set_defaults(fn=cmd_package)

    p = sub.add_parser("import-tests", help="engine test suites (.test/.slt/.sqltest) -> seed .sql files (C6)")
    p.add_argument("paths", nargs="+", help="test files or directories")
    p.add_argument("--out", required=True, help="seed directory (use as generator.params.seeds)")
    p.add_argument("--max-statements", type=int, default=200)
    p.add_argument("--max-files", type=int)
    p.set_defaults(fn=cmd_import_tests)

    p = sub.add_parser("kernels", help="mine rule kernels (minimal firing witnesses) and compose them into seeds")
    p.add_argument("config")
    p.add_argument("--name", help="config (arm) whose generator to use (default: the first)")
    p.add_argument("-n", type=int, default=300, help="generated test cases to mine from")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--per-rule", type=int, default=2, help="kernels to keep per rule")
    p.add_argument("--budget", type=int, default=80, help="reduction runs per kernel")
    p.add_argument("--per-pair", type=int, default=2, help="composition templates per rule pair")
    p.add_argument("--from-json", help="compose from an existing kernels.json instead of mining")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_kernels)

    p = sub.add_parser("ledger", help="precision ledger per engine x oracle from docs/bughunt (D4)")
    p.add_argument("--root", default="../docs/bughunt")
    p.add_argument("--out", help="also write the markdown here")
    p.set_defaults(fn=cmd_ledger)

    a = ap.parse_args(argv)
    _setup_logging(0 if a.quiet else a.verbose)
    return a.fn(a)
