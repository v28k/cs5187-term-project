"""End-to-end: config -> runner -> run logs -> validation -> report, on the mock executor."""

import json
from pathlib import Path

import pytest
import yaml

from pgfuzz.core.interfaces import Executor
from pgfuzz.core.types import ExecResult, StatementResult, StatementStatus, TestCase
from pgfuzz.eval.known_bugs import KnownBugCatalog
from pgfuzz.eval.oracle import classify
from pgfuzz.reference.mock_executor import MockExecutor
from pgfuzz.report import build_report
from pgfuzz.runlog import load_experiment, validate_run
from pgfuzz.runner import load_config, run_experiment
from pgfuzz.runner.config import ConfigError
from pgfuzz.runner.experiment import plan
from pgfuzz.runner.selftest import run_selftest

SRC = Path(__file__).resolve().parents[1]
SEEDS = str(SRC / "corpus" / "seeds")


def _config(tmp_path: Path, **over) -> Path:
    raw = {
        "experiment": "t",
        "output_dir": str(tmp_path / "out"),
        "trials": 2,
        "seed": 1,
        "budget": {"testcases": 300},
        "snapshot_interval_s": 0.01,
        "coverage_interval_s": 0.01,
        "baseline": "random",
        "executor": {"plugin": "pgfuzz.reference.mock_executor:MockExecutor", "params": {"tables": ["t0", "t1"]}},
        "configs": [
            {"name": "random", "generator": {"plugin": "pgfuzz.reference.generators:RandomGenerator", "params": {"mode": "random"}}},
            {"name": "mutation", "generator": {"plugin": "pgfuzz.reference.generators:RandomGenerator", "params": {"mode": "mutation", "seeds": [SEEDS]}}},
            {"name": "off", "enabled": False, "generator": {"plugin": "does.not:Exist"}},
        ],
    }
    raw.update(over)
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "exp.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def _outcomes(trial_dir: Path):
    return [(e["id"], e["outcome"], e.get("sig")) for e in map(json.loads, (trial_dir / "events.jsonl").open()) if e["type"] == "exec"]


def test_end_to_end(tmp_path):
    cfg = load_config(_config(tmp_path))
    run_experiment(cfg)
    groups = load_experiment(cfg.experiment_dir)
    assert sorted(groups) == ["mutation", "random"]
    for trials in groups.values():
        assert len(trials) == 2
        for t in trials:
            assert validate_run(t.path) == []
            assert t.summary["testcases"] == 300
            assert t.summary["stop_reason"] == "budget_testcases"
            assert t.manifest["seed"] == cfg.trial_seed(t.trial)

    # paired seeds: trial k uses the same seed in every config
    assert groups["random"][0].manifest["seed"] == groups["mutation"][0].manifest["seed"]

    out = build_report(cfg.experiment_dir, plots=False)
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "mock executor" in report and "Pairwise comparisons" in report
    assert (out / "table_summary.tex").read_text().count(r"\toprule") == 1
    assert (out / "trials.csv").exists() and (out / "comparison.csv").exists()


def test_failures_are_written_and_deduplicated(tmp_path):
    corpus = tmp_path / "pocs"
    corpus.mkdir()
    (corpus / "a.sql").write_text("SELECT 1;\nSELECT * FROM t0, LATERAL (SELECT rank() OVER () FROM t1) s;\nSELECT 2;\n")
    (corpus / "b.sql").write_text("WITH RECURSIVE r AS (SELECT 1 EXCEPT SELECT 2) SELECT * FROM r;\n")
    (corpus / "c.sql").write_text("SELECT DISTINCT ON (c0) c0, sum(c0) OVER (ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) FROM t0;\n")
    (corpus / "d.sql").write_text("SELECT c0 FROM t0;\n")
    cfg = load_config(_config(tmp_path, trials=1, budget={"testcases": 8}, configs=[
        {"name": "pocs", "generator": {"plugin": "pgfuzz.reference.generators:CorpusGenerator",
                                       "params": {"paths": [str(corpus)], "loop": True}}}], baseline=None))
    run_experiment(cfg)
    trial = load_experiment(cfg.experiment_dir)["pocs"][0]
    assert validate_run(trial.path) == []
    fails = {f["outcome"]: f for f in trial.failures()}
    assert set(fails) == {"crash", "assertion", "internal_error"}
    assert fails["crash"]["culprit"] == 1 and fails["crash"]["details"]["signal"] == 11
    assert fails["assertion"]["details"]["assertion"]["file"] == "nodeRecursiveunion.c"
    for f in fails.values():
        d = trial.path / "failures" / f["signature"]
        assert (d / "testcase.sql").read_text().startswith("-- pgfuzz failure")
        assert (d / "repro-1.sql").exists()  # the corpus looped, so each failure recurred once
    assert trial.summary["bug_candidates"] == 3
    assert {s["count"] for s in trial.summary["signatures"]} == {2}


def test_trials_are_deterministic(tmp_path):
    a = load_config(_config(tmp_path / "a", trials=1))
    b = load_config(_config(tmp_path / "b", trials=1))
    run_experiment(a, only=["mutation"])
    run_experiment(b, only=["mutation"])
    da = a.experiment_dir / "mutation" / "trial-00"
    db = b.experiment_dir / "mutation" / "trial-00"
    assert _outcomes(da) == _outcomes(db)


def test_resume_skips_finished(tmp_path):
    cfg = load_config(_config(tmp_path, trials=1))
    run_experiment(cfg, only=["random"])
    p = plan(cfg)
    assert [(c.name, t) for c, t in p.done] == [("random", 0)]
    assert [(c.name, t) for c, t in p.todo] == [("mutation", 0)]
    assert len(plan(cfg, fresh=True).todo) == 2


def test_config_errors(tmp_path):
    with pytest.raises(ConfigError):
        load_config(_config(tmp_path, budget={}))
    with pytest.raises(ConfigError):
        load_config(_config(tmp_path, baseline="nope"))
    with pytest.raises(ConfigError):
        load_config(_config(tmp_path, experiment="bad name"))


class _FlakyExecutor(Executor):
    """Raises on every 3rd test case and returns too few results on every 5th."""

    def __init__(self):
        self.n = 0

    def execute(self, testcase: TestCase) -> ExecResult:
        self.n += 1
        if self.n % 3 == 0:
            raise ConnectionError("harness hiccup")
        k = len(testcase.statements) - (1 if self.n % 5 == 0 else 0)
        return ExecResult([StatementResult(StatementStatus.OK) for _ in range(k)])


def test_harness_errors_are_logged_not_fatal(tmp_path):
    p = _config(tmp_path, trials=1, budget={"testcases": 60}, max_harness_errors=1000,
                executor={"plugin": "tests.test_pipeline:_FlakyExecutor"})
    cfg = load_config(p)
    run_experiment(cfg, only=["random"])
    t = load_experiment(cfg.experiment_dir)["random"][0]
    assert validate_run(t.path) == []
    errors = [e for e in t.events() if e["type"] == "harness_error"]
    assert len(errors) >= 20
    assert t.summary["harness_errors"] == 20


def test_too_many_harness_errors_stop_trial(tmp_path):
    p = _config(tmp_path, trials=1, budget={"testcases": 60}, max_harness_errors=3,
                executor={"plugin": "tests.test_pipeline:_FlakyExecutor"})
    cfg = load_config(p)
    run_experiment(cfg, only=["random"])
    t = load_experiment(cfg.experiment_dir)["random"][0]
    assert t.summary["stop_reason"] == "harness_failure"


def test_mock_passes_selftest():
    results = run_selftest(MockExecutor())
    assert all(r.passed for r in results), [(r.check.name, r.got, r.error) for r in results if not r.passed]


def test_known_bug_matching(tmp_path):
    p = tmp_path / "kb.yaml"
    p.write_text(yaml.safe_dump({"bugs": [
        {"id": "kb-1", "match": {"outcome": "internal_error", "message_regex": "unrecognized node type"}},
        {"id": "kb-2", "match": {"outcome": "assertion", "assert_regex": r"relnode\.c"}},
    ]}), encoding="utf-8")
    cat = KnownBugCatalog.load(p)
    internal = classify(ExecResult([StatementResult(StatementStatus.ERROR, "XX000", "unrecognized node type: 5")]))
    trap = classify(ExecResult([StatementResult(StatementStatus.CONNECTION_LOST)],
                               server_log=['TRAP: failed Assert("x"), File: "relnode.c", Line: 3, PID: 1']))
    benign = classify(ExecResult([StatementResult(StatementStatus.ERROR, "22012", "unrecognized node type")]))
    assert cat.match(internal) == ["kb-1"]
    assert cat.match(trap) == ["kb-2"]
    assert cat.match(benign) == []
