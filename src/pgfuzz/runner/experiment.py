"""Runs every (configuration, trial) pair of an experiment, optionally in parallel.

Trials are interleaved (trial 0 of every config, then trial 1, ...) so an
interrupted experiment still has a balanced number of trials per config.
Finished trials are skipped on re-run unless ``fresh=True``.
"""

from __future__ import annotations

import json
import logging
import multiprocessing as mp
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pgfuzz.runner.config import ExperimentConfig, FuzzConfig
from pgfuzz.runner.trial import INCOMPLETE, run_trial, trial_dir
from pgfuzz.runlog.writer import write_json_atomic

log = logging.getLogger("pgfuzz.experiment")

_worker_id: int = 0


def _init_worker(counter: Any, level: int) -> None:
    global _worker_id
    with counter.get_lock():
        _worker_id = counter.value
        counter.value += 1
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _run_in_worker(cfg_path: str, config_name: str, trial: int) -> tuple[str, int, dict[str, Any]]:
    from pgfuzz.runner.config import load_config

    cfg = load_config(cfg_path)
    fc = next(c for c in cfg.configs if c.name == config_name)
    return config_name, trial, _short(run_trial(cfg, fc, trial, worker=_worker_id))


def _short(summary: dict[str, Any]) -> dict[str, Any]:
    keys = ("stop_reason", "elapsed_s", "testcases", "valid_query_rate", "features", "bug_candidates")
    return {k: summary.get(k) for k in keys}


def is_finished(path: Path) -> bool:
    s = path / "summary.json"
    if not s.exists():
        return False
    try:
        return json.loads(s.read_text(encoding="utf-8")).get("stop_reason") not in INCOMPLETE
    except (json.JSONDecodeError, OSError):
        return False


@dataclass
class Plan:
    todo: list[tuple[FuzzConfig, int]]
    done: list[tuple[FuzzConfig, int]]


def plan(cfg: ExperimentConfig, only: list[str] | None = None, trials: int | None = None, fresh: bool = False) -> Plan:
    configs = cfg.enabled_configs(only)
    n = trials or cfg.trials
    todo, done = [], []
    for t in range(n):
        for fc in configs:
            (done if (not fresh and is_finished(trial_dir(cfg, fc, t))) else todo).append((fc, t))
    return Plan(todo, done)


def run_experiment(
    cfg: ExperimentConfig,
    jobs: int = 1,
    only: list[str] | None = None,
    trials: int | None = None,
    fresh: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    p = plan(cfg, only, trials, fresh)
    cfg.experiment_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cfg.path, cfg.experiment_dir / f"experiment{cfg.path.suffix}")
    write_json_atomic(
        cfg.experiment_dir / "experiment.json",
        {"v": 1, "experiment": cfg.experiment, "config_file": cfg.path.name, "trials": trials or cfg.trials,
         "configs": [{"name": c.name, "label": c.label} for c in cfg.enabled_configs(only)],
         "baseline": cfg.baseline},
    )
    for fc, t in p.done:
        log.info("skip %s trial %d (finished)", fc.name, t)
    for fc, t in p.todo:
        d = trial_dir(cfg, fc, t)
        if d.exists():
            shutil.rmtree(d)

    results: dict[str, list[dict[str, Any]]] = {}
    if jobs <= 1:
        for fc, t in p.todo:
            log.info("run %s trial %d", fc.name, t)
            results.setdefault(fc.name, []).append(_short(run_trial(cfg, fc, t, worker=0)))
        return results

    counter = mp.get_context("spawn").Value("i", 0)
    level = logging.getLogger().getEffectiveLevel()
    with ProcessPoolExecutor(max_workers=jobs, mp_context=mp.get_context("spawn"),
                             initializer=_init_worker, initargs=(counter, level)) as pool:
        futs = {pool.submit(_run_in_worker, str(cfg.path), fc.name, t): (fc.name, t) for fc, t in p.todo}
        for f in as_completed(futs):
            name, t = futs[f]
            try:
                _, _, s = f.result()
                results.setdefault(name, []).append(s)
                log.info("done %s trial %d: %s", name, t, s)
            except Exception as e:
                log.error("%s trial %d failed: %s", name, t, e)
    return results
