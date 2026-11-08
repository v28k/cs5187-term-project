"""Autonomous campaign agent (D1): run several engine campaigns, triage what is new, package it.

One round = for every config: a campaign of ``budget`` seconds (a temporary copy of the config
with the budget and output directory overridden, run as ``pgfuzz run``, engines in parallel up
to ``jobs``); then ``pgfuzz triage`` on new failures that no known-bug entry matches; then a
package draft (``pgfuzz.agent.package``) for every candidate that reproduced every time. The
round summary goes to ``<out>/HUNT.md``. Nothing is filed anywhere: packages are for a person.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ENGINE_OF = {"duckdb": "duckdb", "sqlite": "sqlite", "turso": "turso", "datafusion": "datafusion"}


def _engine(cfg: dict[str, Any]) -> str:
    ex = json.dumps(cfg.get("executor", {})).lower()
    for k in ("turso", "datafusion", "duckdb", "sqlite"):
        if k in ex:
            return k
    return "postgres"


def _tmp_config(path: Path, budget: float, out_dir: Path) -> tuple[Path, dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["budget"] = {"seconds": budget}
    raw["trials"] = 1
    raw["output_dir"] = str(out_dir.resolve())
    raw["experiment"] = f"hunt_{raw['experiment']}"
    tmp = path.parent / f".hunt_{path.stem}.yaml"
    tmp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return tmp, raw


def new_failures(exp_dir: Path) -> list[Path]:
    out = []
    for f in sorted(exp_dir.glob("*/trial-*/failures/*/failure.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("known_bugs"):
            out.append(f.parent)
    return out


def hunt(configs: list[str], budget: float, out: str, jobs: int = 2, repeat: int = 3,
         max_triage: int = 20, log=print) -> dict[str, Any]:
    out_dir = Path(out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    runs: list[tuple[Path, Path, dict[str, Any], subprocess.Popen]] = []
    summary: dict[str, Any] = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "budget_s": budget, "engines": {}}
    pending = [Path(c).resolve() for c in configs]
    active: list[tuple[Path, Path, dict[str, Any], subprocess.Popen]] = []
    src = Path(__file__).resolve().parents[2]
    while pending or active:
        while pending and len(active) < jobs:
            c = pending.pop(0)
            tmp, raw = _tmp_config(c, budget, out_dir / "campaigns")
            log(f"hunt: start {raw['experiment']} ({budget:.0f} s)")
            p = subprocess.Popen([sys.executable, "-m", "pgfuzz", "-q", "run", str(tmp), "-j", "1", "--fresh",
                                  "--no-report"], cwd=src, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            active.append((c, tmp, raw, p))
        time.sleep(2)
        for item in list(active):
            c, tmp, raw, p = item
            if p.poll() is not None:
                active.remove(item)
                runs.append(item)
                tmp.unlink(missing_ok=True)
                log(f"hunt: done {raw['experiment']} (exit {p.returncode})")
    from pgfuzz.agent.package import make_package

    for c, _tmp, raw, _p in runs:
        engine = _engine(raw)
        exp_dir = out_dir / "campaigns" / raw["experiment"]
        fails = new_failures(exp_dir)[:max_triage]
        eng: dict[str, Any] = {"config": str(c), "new_failures": len(fails), "packages": []}
        if fails:
            tri = out_dir / "triage" / raw["experiment"]
            subprocess.run([sys.executable, "-m", "pgfuzz", "-q", "triage", str(c), *map(str, fails), "--out", str(tri),
                            "--repeat", str(repeat)], cwd=src, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            for t in sorted(tri.glob("*/triage.json")):
                info = json.loads(t.read_text(encoding="utf-8"))
                if str(info.get("reproduced", "")).startswith(f"{repeat}/"):
                    pk = make_package(engine, t.parent, out_dir / "packages")
                    eng["packages"].append(str(pk))
        summary["engines"][raw["experiment"]] = eng
    lines = [f"# Hunt {summary['started']} ({budget:.0f} s per engine)", "",
             "| Campaign | New failures | Reproducible packages |", "|---|---|---|"]
    for name, e in summary["engines"].items():
        lines.append(f"| {name} | {e['new_failures']} | {len(e['packages'])} |")
    lines += ["", "Packages (drafts; confirm, decide the expected result, then follow docs/generalized/HANDOFF.md 1d):", ""]
    lines += [f"- `{p}`" for e in summary["engines"].values() for p in e["packages"]]
    (out_dir / "HUNT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "hunt.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary
