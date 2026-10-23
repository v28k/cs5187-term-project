"""Command line: ``python -m pgfuzz <command> ...`` (run from ``src/``)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


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
    try:
        run_experiment(cfg, jobs=a.jobs, only=only, trials=a.trials, fresh=a.fresh)
    except KeyboardInterrupt:
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
    from pgfuzz.core.sqlsplit import split_statements
    from pgfuzz.core.types import TestCase
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
            stmts = split_statements(Path(f).read_text(encoding="utf-8"))
            tc = TestCase(stmts, origin="replay", id=i)
            for _ in range(a.repeat):
                res = ex.execute(tc)
                cls = oracle.classify(res)
                rec = {"file": f, "outcome": cls.outcome.value, "culprit": cls.culprit, "sqlstate": cls.sqlstate,
                       "message": cls.message}
                if cls.is_bug_candidate:
                    found += 1
                    sig = signature.compute(cls, tc)
                    rec.update(signature=sig.id, strength=sig.strength, known_bugs=catalog.match(cls),
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
    try:
        for i in range(a.n):
            tc = gen.next_testcase()
            if tc is None:
                break
            tc.id = i
            res = ex.execute(tc)
            cls = oracle.classify(res)
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
    print(json.dumps(stats, indent=1))
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
    p.set_defaults(fn=cmd_sample)

    a = ap.parse_args(argv)
    _setup_logging(0 if a.quiet else a.verbose)
    return a.fn(a)
