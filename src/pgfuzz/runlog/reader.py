from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from pgfuzz.runlog.schema import SCHEMA_VERSION


@dataclass
class TrialData:
    path: Path
    config: str
    trial: int
    manifest: dict[str, Any]
    summary: dict[str, Any]
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def events(self) -> Iterator[dict[str, Any]]:
        with (self.path / "events.jsonl").open(encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)

    def failures(self) -> list[dict[str, Any]]:
        out = []
        fd = self.path / "failures"
        if fd.exists():
            for p in sorted(fd.glob("*/failure.json")):
                out.append(json.loads(p.read_text(encoding="utf-8")))
        return out


def _read_json(p: Path) -> dict[str, Any]:
    obj = json.loads(p.read_text(encoding="utf-8"))
    if obj.get("v") != SCHEMA_VERSION:
        raise ValueError(f"{p}: unsupported schema version {obj.get('v')!r}")
    return obj


def load_trial(path: str | Path) -> TrialData:
    p = Path(path)
    manifest = _read_json(p / "manifest.json")
    summary = _read_json(p / "summary.json")
    timeline = []
    tl = p / "timeline.jsonl"
    if tl.exists():
        with tl.open(encoding="utf-8") as f:
            timeline = [json.loads(line) for line in f if line.strip()]
    return TrialData(p, manifest["config"], int(manifest["trial"]), manifest, summary, timeline)


def load_experiment(path: str | Path) -> dict[str, list[TrialData]]:
    """Load every *finished* trial under an experiment directory, grouped by config."""
    root = Path(path)
    groups: dict[str, list[TrialData]] = {}
    for summary in sorted(root.glob("*/trial-*/summary.json")):
        t = load_trial(summary.parent)
        groups.setdefault(t.config, []).append(t)
    for trials in groups.values():
        trials.sort(key=lambda t: t.trial)
    return groups
