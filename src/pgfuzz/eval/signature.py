"""Failure deduplication signatures.

Two failures share a signature when they most likely have the same root cause.
Strength, strongest first:

* ``stack``     top-N symbolized frames of a core dump (if the harness provides them);
* ``assert``    assertion expression + source file;
* ``message``   SQLSTATE + error message with literals/identifiers/numbers abstracted;
* ``weak``      crash with no stack: signal + verb and SQL features of the crashing statement.

``unique bug candidates`` in reports are counted by signature, so the strength is
logged alongside it and reported as a threat to validity.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from pgfuzz.core.types import Outcome, TestCase
from pgfuzz.eval.oracle import Classification
from pgfuzz.eval.features import features_of, statement_shape

STACK_FRAMES = 5

_QUOTED = re.compile(r'"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\'')
_HEX = re.compile(r"\b0x[0-9a-fA-F]+\b")
_NUM = re.compile(r"\b\d+\b")
_WS = re.compile(r"\s+")
_FRAME_ADDR = re.compile(r"^#\d+\s+(?:0x[0-9a-fA-F]+\s+(?:in\s+)?)?")
_FRAME_ARGS = re.compile(r"\s*\(.*$")

# Frames that are present in every crash and carry no root-cause information.
_GENERIC_FRAMES = re.compile(
    r"^(?:(?:raise|abort|pthread_kill|_start|ExceptionalCondition|errfinish|elog_finish|errstart|errstart_cold|"
    r"set_backtrace|backtrace|pg_re_throw|PostgresMain|exec_simple_query|ServerLoop|PostmasterMain|BackendMain|"
    r"BackendStartup|BackendRun|postmaster_child_launch|main|StandardHandlerForSigillSigsegvSigbus)\b"
    r"|__GI_|__libc_|__pthread_|__asan|__interceptor_|__sanitizer|__ubsan|_ZN11__sanitizer|_ZN6__asan)"
)


@dataclass(frozen=True)
class Signature:
    id: str
    strength: str
    key: str


def normalize_message(msg: str | None) -> str:
    if not msg:
        return ""
    msg = msg.splitlines()[0]
    msg = _QUOTED.sub("?", msg)
    msg = _HEX.sub("H", msg)
    msg = _NUM.sub("N", msg)
    return _WS.sub(" ", msg).strip()


def normalize_frames(frames: list[str], n: int = STACK_FRAMES) -> list[str]:
    out = []
    for f in frames:
        name = _FRAME_ARGS.sub("", _FRAME_ADDR.sub("", f.strip()))
        if not name or _GENERIC_FRAMES.match(name):
            continue
        out.append(name)
        if len(out) == n:
            break
    return out


def compute(cls: Classification, testcase: TestCase | None = None) -> Signature:
    kind = cls.outcome.value
    d = cls.details
    frames = normalize_frames(d.get("backtrace") or [])
    if cls.outcome is Outcome.WRONG_RESULT:
        strength, key = "diff", f"{kind}|{d.get('variant', '?')}|{_culprit_shape(cls, testcase)}"
    elif frames:
        strength, key = "stack", f"{kind}|" + "<".join(frames)
    elif "assertion" in d:
        a = d["assertion"]
        strength, key = "assert", f"{kind}|{a['file']}|{normalize_message(a['expr'])}"
    elif "sanitizer" in d:
        s = d["sanitizer"]
        strength, key = "sanitizer", f"{kind}|{s.get('tool')}|{normalize_message(s.get('kind'))}|{s.get('file', '')}"
    elif d.get("panic") or (cls.message and not d.get("connection_lost")):
        msg = normalize_message(d.get("panic") or cls.message)
        strength, key = "message", f"{kind}|{cls.sqlstate or '-'}|{msg}"
    else:
        # The client only sees "server closed the connection unexpectedly", which is
        # the same for every crash, so fall back to what the crashing statement did.
        strength, key = "weak", f"{kind}|sig={d.get('signal', '?')}|{_culprit_shape(cls, testcase)}"
    return Signature(hashlib.sha1(key.encode()).hexdigest()[:12], strength, key)


def _culprit_shape(cls: Classification, testcase: TestCase | None) -> str:
    if testcase is None or cls.culprit is None or cls.culprit >= len(testcase.statements):
        return ""
    sql = testcase.statements[cls.culprit]
    feats = sorted(f for f in features_of(sql) if not f.startswith("stmt:"))
    verb = (statement_shape(sql).split() or ["?"])[0]
    return f"{verb}|{','.join(feats)}"
