from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TextIO

from pgfuzz.core.types import ExecResult, TestCase
from pgfuzz.eval.oracle import Classification
from pgfuzz.eval.signature import Signature
from pgfuzz.runlog.schema import SCHEMA_VERSION

MAX_MSG = 500


def write_json_atomic(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _trunc(s: str | None, n: int = MAX_MSG) -> str | None:
    if s is None:
        return None
    s = s.splitlines()[0] if s else s
    return s if len(s) <= n else s[: n - 3] + "..."


class RunLog:
    """Writes one trial directory in the format described in ``pgfuzz.runlog.schema``.

    ``log_sql``: ``"none"`` | ``"failures"`` | ``"all"`` controls whether SQL text is
    stored in ``events.jsonl`` (failures always get a ``testcase.sql``).
    """

    def __init__(self, trial_dir: Path, log_sql: str = "failures", max_repros: int = 3, flush_every: int = 200) -> None:
        self.dir = trial_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "failures").mkdir(exist_ok=True)
        self.log_sql = log_sql
        self.max_repros = max_repros
        self.flush_every = flush_every
        self._events: TextIO = (self.dir / "events.jsonl").open("w", encoding="utf-8", newline="\n")
        self._timeline: TextIO = (self.dir / "timeline.jsonl").open("w", encoding="utf-8", newline="\n")
        self._pending = 0
        self._repro_counts: dict[str, int] = {}

    def _emit(self, f: TextIO, rec: dict[str, Any]) -> None:
        f.write(json.dumps(rec, separators=(",", ":"), default=str) + "\n")
        self._pending += 1
        if self._pending >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        self._events.flush()
        self._timeline.flush()
        self._pending = 0

    def manifest(self, data: dict[str, Any]) -> None:
        write_json_atomic(self.dir / "manifest.json", {"v": SCHEMA_VERSION, **data})

    def exec_event(
        self,
        t: float,
        tc: TestCase,
        res: ExecResult,
        cls: Classification,
        sig: Signature | None,
        sig_new: bool,
        new_features: frozenset[str],
        parsed: int,
        ok: int,
    ) -> None:
        rec: dict[str, Any] = {
            "v": SCHEMA_VERSION,
            "type": "exec",
            "t": round(t, 4),
            "id": tc.id,
            "origin": tc.origin,
            "n": len(tc.statements),
            "outcome": cls.outcome.value,
            "ms": round(res.wall_ms, 3),
            "parsed": parsed,
            "ok": ok,
        }
        if cls.culprit is not None:
            rec["culprit"] = cls.culprit
            rec["sqlstate"] = cls.sqlstate
            rec["msg"] = _trunc(cls.message)
        if sig is not None:
            rec["sig"] = sig.id
            rec["sig_new"] = sig_new
        if new_features:
            rec["feat_new"] = sorted(new_features)
        if any(o.value != "ok" for o in cls.statement_outcomes):
            rec["so"] = [o.value for o in cls.statement_outcomes]
        if self.log_sql == "all" or (self.log_sql == "failures" and cls.is_bug_candidate):
            rec["sql"] = tc.statements
        if tc.meta:
            rec["meta"] = tc.meta
        self._emit(self._events, rec)

    def harness_error(self, t: float, tc_id: int, error: str, fatal: bool) -> None:
        self._emit(self._events, {"v": SCHEMA_VERSION, "type": "harness_error", "t": round(t, 4), "id": tc_id,
                                  "error": _trunc(error, 2000), "fatal": fatal})

    def note(self, t: float, msg: str) -> None:
        self._emit(self._events, {"v": SCHEMA_VERSION, "type": "note", "t": round(t, 4), "msg": msg})

    def timeline(self, snap: dict[str, Any]) -> None:
        self._emit(self._timeline, {"v": SCHEMA_VERSION, **snap})

    def failure(
        self,
        t: float,
        tc: TestCase,
        res: ExecResult,
        cls: Classification,
        sig: Signature,
        sig_new: bool,
        known: list[str],
    ) -> None:
        d = self.dir / "failures" / sig.id
        if sig_new:
            d.mkdir(parents=True, exist_ok=True)
            (d / "testcase.sql").write_text(_sql_header(tc, cls, sig) + tc.to_sql(), encoding="utf-8")
            write_json_atomic(
                d / "failure.json",
                {
                    "v": SCHEMA_VERSION,
                    "signature": sig.id,
                    "strength": sig.strength,
                    "key": sig.key,
                    "outcome": cls.outcome.value,
                    "sqlstate": cls.sqlstate,
                    "message": cls.message,
                    "culprit": cls.culprit,
                    "culprit_sql": tc.statements[cls.culprit] if cls.culprit is not None and cls.culprit < len(tc.statements) else None,
                    "details": cls.details,
                    "known_bugs": known,
                    "first_t": round(t, 3),
                    "testcase_id": tc.id,
                    "origin": tc.origin,
                    "meta": tc.meta,
                    "statements": [r.to_dict() for r in res.statements],
                    "server_log": res.server_log[-200:],
                    "extra": res.extra,
                },
            )
            self._repro_counts[sig.id] = 0
        else:
            k = self._repro_counts.get(sig.id, 0)
            if k < self.max_repros:
                (d / f"repro-{k + 1}.sql").write_text(_sql_header(tc, cls, sig) + tc.to_sql(), encoding="utf-8")
                self._repro_counts[sig.id] = k + 1

    def summary(self, data: dict[str, Any]) -> None:
        self.flush()
        write_json_atomic(self.dir / "summary.json", {"v": SCHEMA_VERSION, **data})

    def close(self) -> None:
        for f in (self._events, self._timeline):
            if not f.closed:
                f.flush()
                f.close()


def _sql_header(tc: TestCase, cls: Classification, sig: Signature) -> str:
    lines = [
        f"-- pgfuzz failure {sig.id} ({cls.outcome.value}, signature strength: {sig.strength})",
        f"-- test case {tc.id} from {tc.origin or '?'}",
    ]
    if cls.sqlstate or cls.message:
        lines.append(f"-- SQLSTATE {cls.sqlstate or '-'}: {_trunc(cls.message, 200) or ''}")
    if cls.culprit is not None:
        lines.append(f"-- failing statement: #{cls.culprit + 1}")
    return "\n".join(lines) + "\n"
