"""Experiment configuration (YAML or JSON).

Relative paths in the file (``output_dir``, ``known_bugs``) are resolved against
the directory containing the config file. Plug-in ``params`` may use the
placeholders ``{config_dir}``, ``{worker}``, ``{trial}``, ``{config}`` and
``{port}`` (= ``base_port + worker``); they let parallel trials use separate
PostgreSQL instances, e.g. ``dsn: "host=localhost port={port}"``. Rendered values are strings.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
LOG_SQL_MODES = ("none", "failures", "all")


class ConfigError(ValueError):
    pass


@dataclass
class PluginSpec:
    plugin: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, obj: Any, where: str) -> "PluginSpec":
        if isinstance(obj, str):
            return cls(obj)
        if not isinstance(obj, dict) or "plugin" not in obj:
            raise ConfigError(f"{where}: expected {{plugin: 'module:Class', params: {{...}}}}")
        params = obj.get("params") or {}
        if not isinstance(params, dict):
            raise ConfigError(f"{where}.params must be a mapping")
        return cls(str(obj["plugin"]), params)

    def render(self, **subst: Any) -> dict[str, Any]:
        return _render(copy.deepcopy(self.params), subst)


@dataclass
class FuzzConfig:
    """One arm of the comparison (e.g. ``random``, ``grammar``, ``grammar_llm``)."""

    name: str
    label: str
    generator: PluginSpec
    executor: PluginSpec | None = None
    enabled: bool = True


@dataclass
class Budget:
    seconds: float | None = None
    testcases: int | None = None

    def describe(self) -> dict[str, Any]:
        return {"seconds": self.seconds, "testcases": self.testcases}


@dataclass
class ExperimentConfig:
    experiment: str
    path: Path
    output_dir: Path
    trials: int
    seed: int
    budget: Budget
    executor: PluginSpec
    configs: list[FuzzConfig]
    coverage_interval_s: float = 30.0
    snapshot_interval_s: float = 5.0
    log_sql: str = "failures"
    max_repros: int = 3
    known_bugs: Path | None = None
    max_harness_errors: int = 20
    baseline: str | None = None
    base_port: int = 5432
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def config_dir(self) -> Path:
        return self.path.parent

    @property
    def experiment_dir(self) -> Path:
        return self.output_dir / self.experiment

    def enabled_configs(self, only: list[str] | None = None) -> list[FuzzConfig]:
        cfgs = [c for c in self.configs if c.enabled]
        if only:
            unknown = set(only) - {c.name for c in self.configs}
            if unknown:
                raise ConfigError(f"unknown config(s): {', '.join(sorted(unknown))}")
            cfgs = [c for c in self.configs if c.name in only]
        return cfgs

    def substitutions(self, config: str, worker: int, trial: int) -> dict[str, Any]:
        """Placeholders available in plug-in params. ``{port}`` is ``base_port + worker``,
        so N parallel workers can use N servers on consecutive ports."""
        return {"config_dir": str(self.config_dir), "worker": worker, "trial": trial, "config": config,
                "port": self.base_port + worker}

    def trial_seed(self, trial: int) -> int:
        """Seed for trial ``trial``. Identical across configs, so trial k of every
        arm starts from the same seed (paired design)."""
        h = hashlib.sha256(f"{self.seed}:{trial}".encode()).digest()
        return int.from_bytes(h[:8], "big") & (2**63 - 1)


def _render(obj: Any, subst: dict[str, Any]) -> Any:
    if isinstance(obj, str):
        try:
            return obj.format(**subst) if "{" in obj else obj
        except (KeyError, IndexError, ValueError):
            return obj
    if isinstance(obj, list):
        return [_render(x, subst) for x in obj]
    if isinstance(obj, dict):
        return {k: _render(v, subst) for k, v in obj.items()}
    return obj


def _positive(v: Any, name: str, kind: type = float, allow_none: bool = True) -> Any:
    if v is None:
        if allow_none:
            return None
        raise ConfigError(f"{name} is required")
    try:
        v = kind(v)
    except (TypeError, ValueError) as e:
        raise ConfigError(f"{name} must be a number") from e
    if v <= 0:
        raise ConfigError(f"{name} must be > 0")
    return v


def load_config(path: str | Path) -> ExperimentConfig:
    path = Path(path).resolve()
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        import yaml

        raw = yaml.safe_load(text)
    else:
        raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return parse_config(raw, path)


def parse_config(raw: dict[str, Any], path: Path) -> ExperimentConfig:
    base = path.parent

    def resolve(p: Any) -> Path | None:
        if p in (None, ""):
            return None
        q = Path(str(p))
        return q if q.is_absolute() else (base / q).resolve()

    name = str(raw.get("experiment") or "")
    if not _NAME.match(name):
        raise ConfigError("experiment: required, letters/digits/._- only")

    b = raw.get("budget") or {}
    budget = Budget(_positive(b.get("seconds"), "budget.seconds"), _positive(b.get("testcases"), "budget.testcases", int))
    if budget.seconds is None and budget.testcases is None:
        raise ConfigError("budget: set at least one of 'seconds' or 'testcases'")

    if "executor" not in raw:
        raise ConfigError("executor: required")
    executor = PluginSpec.parse(raw["executor"], "executor")

    configs = []
    for i, c in enumerate(raw.get("configs") or []):
        where = f"configs[{i}]"
        if not isinstance(c, dict) or "name" not in c or "generator" not in c:
            raise ConfigError(f"{where}: needs 'name' and 'generator'")
        if not _NAME.match(str(c["name"])):
            raise ConfigError(f"{where}.name: letters/digits/._- only")
        configs.append(
            FuzzConfig(
                name=str(c["name"]),
                label=str(c.get("label") or c["name"]),
                generator=PluginSpec.parse(c["generator"], f"{where}.generator"),
                executor=PluginSpec.parse(c["executor"], f"{where}.executor") if c.get("executor") else None,
                enabled=bool(c.get("enabled", True)),
            )
        )
    if not configs:
        raise ConfigError("configs: at least one configuration is required")
    names = [c.name for c in configs]
    if len(set(names)) != len(names):
        raise ConfigError("configs: names must be unique")

    log_sql = str(raw.get("log_sql", "failures"))
    if log_sql not in LOG_SQL_MODES:
        raise ConfigError(f"log_sql must be one of {LOG_SQL_MODES}")

    baseline = raw.get("baseline")
    if baseline is not None and baseline not in names:
        raise ConfigError(f"baseline {baseline!r} is not a config name")

    return ExperimentConfig(
        experiment=name,
        path=path,
        output_dir=resolve(raw.get("output_dir", "results")) or base / "results",
        trials=_positive(raw.get("trials", 1), "trials", int, allow_none=False),
        seed=int(raw.get("seed", 0)),
        budget=budget,
        executor=executor,
        configs=configs,
        coverage_interval_s=_positive(raw.get("coverage_interval_s", 30), "coverage_interval_s"),
        snapshot_interval_s=_positive(raw.get("snapshot_interval_s", 5), "snapshot_interval_s"),
        log_sql=log_sql,
        max_repros=int(raw.get("max_repros", 3)),
        known_bugs=resolve(raw.get("known_bugs")),
        max_harness_errors=_positive(raw.get("max_harness_errors", 20), "max_harness_errors", int),
        baseline=baseline,
        base_port=int(raw.get("base_port", 5432)),
        raw=raw,
    )
