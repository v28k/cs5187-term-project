"""Known-bug catalog used for the "reproduction of known PostgreSQL bugs" metric.

Each entry describes how to recognise a known bug in our oracle's terms. Every
entry must point at a real, public source (pgsql-bugs thread, commit, CVE) and
name the affected server version, because results are only meaningful when the
fuzzer runs against a build that still contains the bug.

YAML format::

    bugs:
      - id: pg-bug-18xxx               # unique, stable id
        title: short description
        source: https://www.postgresql.org/message-id/...
        fixed_in: commit-sha or release
        affected: "16.0 - 16.2"
        match:                         # all given fields must match
          outcome: assertion           # Outcome value
          sqlstate: XX000
          message_regex: "..."
          assert_regex: "..."          # matched against 'file: expr'
          frame_regex: "..."           # matched against any normalized frame
          offline: true                # never matched online; attributed afterwards (wrong results)
        poc: pocs/pg-bug-18xxx.sql     # optional, replayed by 'pgfuzz replay'
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pgfuzz.eval.oracle import Classification
from pgfuzz.eval.signature import normalize_frames


@dataclass
class KnownBug:
    id: str
    title: str = ""
    source: str = ""
    affected: str = ""
    fixed_in: str = ""
    poc: str | None = None
    outcome: str | None = None
    sqlstate: str | None = None
    message_re: re.Pattern[str] | None = None
    assert_re: re.Pattern[str] | None = None
    frame_re: re.Pattern[str] | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def matches(self, cls: Classification) -> bool:
        if self.raw.get("match", {}).get("offline"):   # attributed after the campaign (pgfuzz.bench)
            return False
        if self.outcome and cls.outcome.value != self.outcome:
            return False
        if self.sqlstate and (cls.sqlstate or "").upper() != self.sqlstate.upper():
            return False
        if self.message_re and not self.message_re.search(cls.message or cls.details.get("panic", "") or ""):
            return False
        if self.assert_re:
            a = cls.details.get("assertion")
            if not a or not self.assert_re.search(f"{a['file']}: {a['expr']}"):
                return False
        if self.frame_re:
            frames = normalize_frames(cls.details.get("backtrace") or [], n=50)
            if not any(self.frame_re.search(f) for f in frames):
                return False
        return True


class KnownBugCatalog:
    def __init__(self, bugs: list[KnownBug], root: Path | None = None) -> None:
        self.bugs = bugs
        self.root = root

    def __len__(self) -> int:
        return len(self.bugs)

    @classmethod
    def load(cls, path: str | Path | None) -> "KnownBugCatalog":
        if not path:
            return cls([])
        import yaml

        path = Path(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        bugs = []
        seen = set()
        for e in data.get("bugs") or []:
            if e["id"] in seen:
                raise ValueError(f"duplicate known-bug id {e['id']!r} in {path}")
            seen.add(e["id"])
            m = e.get("match") or {}
            if not m:
                raise ValueError(f"known bug {e['id']!r} has no 'match' criteria")
            bugs.append(
                KnownBug(
                    id=e["id"],
                    title=e.get("title", ""),
                    source=e.get("source", ""),
                    affected=str(e.get("affected", "")),
                    fixed_in=str(e.get("fixed_in", "")),
                    poc=e.get("poc"),
                    outcome=m.get("outcome"),
                    sqlstate=m.get("sqlstate"),
                    message_re=re.compile(m["message_regex"]) if m.get("message_regex") else None,
                    assert_re=re.compile(m["assert_regex"]) if m.get("assert_regex") else None,
                    frame_re=re.compile(m["frame_regex"]) if m.get("frame_regex") else None,
                    raw=e,
                )
            )
        return cls(bugs, path.parent)

    def match(self, cls: Classification) -> list[str]:
        if not cls.is_bug_candidate:
            return []
        return [b.id for b in self.bugs if b.matches(cls)]
