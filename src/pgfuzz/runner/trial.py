"""One trial = one (configuration, repetition) pair under a fixed budget."""

from __future__ import annotations

import datetime as dt
import logging
import platform
import random
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import pgfuzz
from pgfuzz.core.interfaces import Executor, Feedback, Generator, GeneratorContext
from pgfuzz.core.plugins import instantiate
from pgfuzz.core.types import ExecResult, StatementResult, StatementStatus, TestCase
from pgfuzz.eval import oracle, signature
from pgfuzz.eval.known_bugs import KnownBugCatalog
from pgfuzz.eval.metrics import TrialMetrics
from pgfuzz.runlog.writer import RunLog
from pgfuzz.runner.config import ExperimentConfig, FuzzConfig

log = logging.getLogger("pgfuzz.trial")

# Stop reasons. Trials that ended with an INCOMPLETE reason are re-run on resume.
BUDGET_TIME = "budget_seconds"
BUDGET_TESTCASES = "budget_testcases"
EXHAUSTED = "generator_exhausted"
HARNESS_FAILURE = "harness_failure"
INTERRUPTED = "interrupted"
ERROR = "error"
INCOMPLETE = frozenset({INTERRUPTED, ERROR})


def trial_dir(cfg: ExperimentConfig, fc: FuzzConfig, trial: int) -> Path:
    return cfg.experiment_dir / fc.name / f"trial-{trial:02d}"


def _git_commit(path: Path) -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, timeout=5)
        if out.returncode != 0:
            return None
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=path, capture_output=True, text=True, timeout=5)
        return out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return None


def _env() -> dict[str, Any]:
    return {
        "pgfuzz": pgfuzz.__version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "git_commit": _git_commit(Path(__file__).resolve().parent),
    }


def _conform(tc: TestCase, res: ExecResult) -> str | None:
    """Enforce the executor contract: exactly one result per statement."""
    n, m = len(tc.statements), len(res.statements)
    if n == m:
        return None
    if m < n:
        res.statements.extend(StatementResult(StatementStatus.SKIPPED) for _ in range(n - m))
    else:
        del res.statements[n:]
    return f"executor returned {m} results for {n} statements"


def _safe_stats(generator: Generator) -> dict[str, Any]:
    fn = getattr(generator, "stats", None)
    if not callable(fn):
        return {}
    try:
        return dict(fn())
    except Exception as e:  # statistics must never fail a trial
        return {"error": f"{type(e).__name__}: {e}"}


def run_trial(cfg: ExperimentConfig, fc: FuzzConfig, trial: int, worker: int = 0) -> dict[str, Any]:
    out = trial_dir(cfg, fc, trial)
    seed = cfg.trial_seed(trial)
    subst = cfg.substitutions(fc.name, worker, trial)

    exec_spec = fc.executor or cfg.executor
    executor = instantiate(exec_spec.plugin, Executor, exec_spec.render(**subst))
    generator = instantiate(fc.generator.plugin, Generator, fc.generator.render(**subst))
    catalog = KnownBugCatalog.load(cfg.known_bugs)

    runlog = RunLog(out, log_sql=cfg.log_sql, max_repros=cfg.max_repros)
    metrics = TrialMetrics()
    started_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    stop_reason = ERROR
    harness_errors = 0
    t0 = time.monotonic()
    paused = 0.0  # time spent measuring coverage; not charged to the fuzzing budget

    def elapsed() -> float:
        return time.monotonic() - t0 - paused

    def sample_coverage() -> Any:
        nonlocal paused
        s = time.monotonic()
        try:
            return executor.sample_coverage()
        finally:
            paused += time.monotonic() - s

    try:
        executor.start()
        work = out / "work"
        work.mkdir(exist_ok=True)
        ctx = GeneratorContext(seed=seed, rng=random.Random(seed), workdir=work, trial=trial, config_name=fc.name)
        generator.setup(ctx)
        runlog.manifest(
            {
                "experiment": cfg.experiment,
                "config": fc.name,
                "label": fc.label,
                "trial": trial,
                "seed": seed,
                "worker": worker,
                "budget": cfg.budget.describe(),
                "generator": {"plugin": fc.generator.plugin, "params": fc.generator.render(**subst), **generator.describe()},
                "executor": {"plugin": exec_spec.plugin, "params": exec_spec.render(**subst), **executor.describe()},
                "known_bugs": {"catalog": str(cfg.known_bugs) if cfg.known_bugs else None, "entries": len(catalog)},
                "coverage_interval_s": cfg.coverage_interval_s,
                "snapshot_interval_s": cfg.snapshot_interval_s,
                "started_at": started_at,
                "env": _env(),
            }
        )

        t0 = time.monotonic()
        metrics.coverage = sample_coverage()
        runlog.timeline(metrics.snapshot(0.0))
        last_cov = last_snap = 0.0
        next_id = 0

        while True:
            now = elapsed()
            if cfg.budget.seconds is not None and now >= cfg.budget.seconds:
                stop_reason = BUDGET_TIME
                break
            if cfg.budget.testcases is not None and next_id >= cfg.budget.testcases:
                stop_reason = BUDGET_TESTCASES
                break

            tc = generator.next_testcase()
            if tc is None:
                stop_reason = EXHAUSTED
                break
            tc.id = next_id
            next_id += 1
            if not tc.origin:
                tc.origin = generator.name

            try:
                res = executor.execute(tc)
            except Exception as e:  # harness bug or unrecoverable target
                harness_errors += 1
                fatal = harness_errors >= cfg.max_harness_errors
                runlog.harness_error(elapsed(), tc.id, f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=5)}", fatal)
                log.warning("[%s/%d] harness error on test case %d: %s", fc.name, trial, tc.id, e)
                if fatal:
                    stop_reason = HARNESS_FAILURE
                    break
                continue

            problem = _conform(tc, res)
            if problem:
                runlog.harness_error(elapsed(), tc.id, problem, False)

            t = elapsed()
            cls = oracle.classify(res)
            sig = signature.compute(cls, tc) if cls.is_bug_candidate else None
            known = catalog.match(cls) if sig else []
            upd = metrics.update(t, tc, res, cls, sig, known)
            parsed = sum(1 for o, st in zip(upd.statement_outcomes, res.statements) if o.parsed and st.status is not StatementStatus.SKIPPED)
            ok = sum(1 for o, st in zip(upd.statement_outcomes, res.statements) if o.value == "ok" and st.status is not StatementStatus.SKIPPED)
            runlog.exec_event(t, tc, res, cls, sig, upd.new_signature, upd.new_features, parsed, ok)
            if sig is not None:
                runlog.failure(t, tc, res, cls, sig, upd.new_signature, known)
                if upd.new_signature:
                    log.info("[%s/%d] new %s %s at %.1fs: %s", fc.name, trial, cls.outcome.value, sig.id, t, (cls.message or "")[:120])

            generator.feedback(
                Feedback(tc, res, cls.outcome, upd.statement_outcomes, upd.new_features, upd.new_signature, metrics.coverage)
            )

            if t - last_cov >= cfg.coverage_interval_s:
                cov = sample_coverage()
                if cov is not None:
                    metrics.coverage = cov
                last_cov = elapsed()
            if t - last_snap >= cfg.snapshot_interval_s:
                metrics.elapsed = t
                runlog.timeline(metrics.snapshot(t))
                last_snap = t
    except KeyboardInterrupt:
        stop_reason = INTERRUPTED
        raise
    except Exception as e:
        stop_reason = ERROR
        runlog.harness_error(elapsed(), -1, f"{type(e).__name__}: {e}\n{traceback.format_exc()}", True)
        log.error("[%s/%d] trial failed: %s", fc.name, trial, e)
        raise
    finally:
        end = elapsed()
        try:
            cov = sample_coverage()
            if cov is not None:
                metrics.coverage = cov
        except Exception as e:  # coverage is best effort at shutdown
            runlog.note(end, f"final coverage sample failed: {e}")
        metrics.elapsed = end
        runlog.timeline(metrics.snapshot(end))
        summary = {
            "experiment": cfg.experiment,
            "config": fc.name,
            "label": fc.label,
            "trial": trial,
            "seed": seed,
            "stop_reason": stop_reason,
            "harness_errors": harness_errors,
            "coverage_overhead_s": round(paused, 3),
            "generator_stats": _safe_stats(generator),
            "executor_stats": dict(getattr(executor, "diff_stats", {}) or {}),
            "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            **metrics.summary(),
            "signatures": [vars(r) for r in sorted(metrics.signatures.values(), key=lambda r: r.first_t)],
        }
        runlog.summary(summary)
        runlog.close()
        for closer in (generator.close, executor.stop):
            try:
                closer()
            except Exception as e:
                log.warning("cleanup failed: %s", e)
    return summary
