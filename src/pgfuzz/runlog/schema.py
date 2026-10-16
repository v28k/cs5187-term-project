"""Run-log format, version 1.

One trial = one directory::

    <out>/<experiment>/<config>/trial-<NN>/
        manifest.json        what ran: config, seed, plug-in descriptions, versions, host, git commit
        events.jsonl         one JSON object per line (see EVENT_FIELDS)
        timeline.jsonl       periodic metric snapshots (coverage, features, bugs over time)
        summary.json         final metrics (pgfuzz.eval.metrics.TrialMetrics.summary)
        failures/<sig>/      one directory per unique bug-candidate signature
            failure.json     classification, signature key, raw statement results, server log
            testcase.sql     the first test case that produced it, ready to replay with psql
            repro-<k>.sql    up to N further test cases with the same signature

Every JSON record carries ``"v": 1``. Readers must reject unknown major versions.
Times ``t`` are seconds since trial start (monotonic clock).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pgfuzz.core.types import Outcome

SCHEMA_VERSION = 1

_OUTCOMES = {o.value for o in Outcome}

# field -> (type(s), required)
EVENT_FIELDS: dict[str, dict[str, tuple[tuple[type, ...], bool]]] = {
    "exec": {
        "v": ((int,), True),
        "type": ((str,), True),
        "t": ((int, float), True),
        "id": ((int,), True),
        "origin": ((str,), True),
        "n": ((int,), True),
        "outcome": ((str,), True),
        "ms": ((int, float), True),
        "parsed": ((int,), True),
        "ok": ((int,), True),
        "culprit": ((int, type(None)), False),
        "sqlstate": ((str, type(None)), False),
        "msg": ((str, type(None)), False),
        "sig": ((str,), False),
        "sig_new": ((bool,), False),
        "feat_new": ((list,), False),
        "so": ((list,), False),
        "sql": ((list,), False),
        "meta": ((dict,), False),
    },
    "harness_error": {
        "v": ((int,), True),
        "type": ((str,), True),
        "t": ((int, float), True),
        "id": ((int,), True),
        "error": ((str,), True),
        "fatal": ((bool,), True),
    },
    "note": {
        "v": ((int,), True),
        "type": ((str,), True),
        "t": ((int, float), True),
        "msg": ((str,), True),
    },
}

TIMELINE_REQUIRED = ("v", "t", "testcases", "statements", "parse_valid", "valid", "features", "bug_candidates")
MANIFEST_REQUIRED = ("v", "experiment", "config", "trial", "seed", "generator", "executor", "budget", "started_at", "env")
SUMMARY_REQUIRED = (
    "v", "elapsed_s", "testcases", "statements", "parse_valid_rate", "valid_query_rate",
    "feature_coverage", "bug_candidates", "stop_reason",
)


def validate_event(rec: Any) -> list[str]:
    if not isinstance(rec, dict):
        return ["record is not an object"]
    if rec.get("v") != SCHEMA_VERSION:
        return [f"unsupported schema version {rec.get('v')!r}"]
    spec = EVENT_FIELDS.get(rec.get("type"))  # type: ignore[arg-type]
    if spec is None:
        return [f"unknown event type {rec.get('type')!r}"]
    errs = []
    for name, (types, required) in spec.items():
        if name not in rec:
            if required:
                errs.append(f"missing field {name!r}")
            continue
        if not isinstance(rec[name], types) or (isinstance(rec[name], bool) and bool not in types):
            errs.append(f"field {name!r} has type {type(rec[name]).__name__}")
    for name in rec:
        if name not in spec:
            errs.append(f"unknown field {name!r}")
    if rec.get("type") == "exec":
        if rec.get("outcome") not in _OUTCOMES:
            errs.append(f"unknown outcome {rec.get('outcome')!r}")
        so = rec.get("so")
        if so is not None and (len(so) != rec.get("n") or any(o not in _OUTCOMES for o in so)):
            errs.append("'so' must list one valid outcome per statement")
    return errs


def _check_keys(obj: Any, required: tuple[str, ...], what: str) -> list[str]:
    if not isinstance(obj, dict):
        return [f"{what}: not an object"]
    errs = [f"{what}: missing {k!r}" for k in required if k not in obj]
    if obj.get("v") not in (None, SCHEMA_VERSION):
        errs.append(f"{what}: unsupported schema version {obj.get('v')!r}")
    return errs


def validate_run(trial_dir: str | Path, max_errors: int = 50) -> list[str]:
    """Validate one trial directory. Returns a list of problems (empty = valid)."""
    d = Path(trial_dir)
    errs: list[str] = []
    for name, req in (("manifest.json", MANIFEST_REQUIRED), ("summary.json", SUMMARY_REQUIRED)):
        p = d / name
        if not p.exists():
            errs.append(f"{name}: missing")
            continue
        try:
            errs += _check_keys(json.loads(p.read_text(encoding="utf-8")), req, name)
        except json.JSONDecodeError as e:
            errs.append(f"{name}: invalid JSON ({e})")

    last_t = -1.0
    seen_ids: set[int] = set()
    ev = d / "events.jsonl"
    if not ev.exists():
        errs.append("events.jsonl: missing")
    else:
        with ev.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if len(errs) >= max_errors:
                    break
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as e:
                    errs.append(f"events.jsonl:{lineno}: invalid JSON ({e})")
                    continue
                errs += [f"events.jsonl:{lineno}: {e}" for e in validate_event(rec)]
                t = rec.get("t", 0)
                if isinstance(t, (int, float)):
                    if t + 1e-6 < last_t:
                        errs.append(f"events.jsonl:{lineno}: time goes backwards")
                    last_t = max(last_t, t)
                if rec.get("type") == "exec":
                    if rec.get("id") in seen_ids:
                        errs.append(f"events.jsonl:{lineno}: duplicate test-case id {rec.get('id')}")
                    seen_ids.add(rec.get("id"))  # type: ignore[arg-type]

    tl = d / "timeline.jsonl"
    if tl.exists():
        with tl.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                try:
                    errs += _check_keys(json.loads(line), TIMELINE_REQUIRED, f"timeline.jsonl:{lineno}")
                except json.JSONDecodeError as e:
                    errs.append(f"timeline.jsonl:{lineno}: invalid JSON ({e})")
    else:
        errs.append("timeline.jsonl: missing")

    fd = d / "failures"
    if fd.exists():
        for sub in sorted(p for p in fd.iterdir() if p.is_dir()):
            for need in ("failure.json", "testcase.sql"):
                if not (sub / need).exists():
                    errs.append(f"failures/{sub.name}: missing {need}")
    return errs[:max_errors]
