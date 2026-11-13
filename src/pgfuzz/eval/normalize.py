"""Value normalizers for cross-engine differential testing.

Two engines that are both correct can still print the same value differently (Turso
renders REAL as text with 15 significant digits, SQLite >= 3.47 with the shortest
round-trip form; one engine returns 2.0 where the other returns 2). A normalizer maps every
rendered value (a string, as produced by ``pgfuzz.targets.base``) to a canonical form
*before* the result digest is computed, so such differences do not become candidates.

Normalizers are data: a pair's list lives in its config (``normalize: [...]``), and task C4
infers the list automatically from probe disagreements. Each normalizer is a function
``str | None -> str | None``.
"""

from __future__ import annotations

import re
from typing import Callable

_NUM = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")
_NUM_IN_TEXT = re.compile(r"[+-]?\d+\.\d{15,}(?:[eE][+-]?\d+)?|[+-]?\d\.\d{14,}[eE][+-]?\d+")


def _float_text_15(v: str | None) -> str | None:
    """Numbers with more than 15 significant digits inside any value -> %.15g."""
    if v is None:
        return None
    return _NUM_IN_TEXT.sub(lambda m: format(float(m.group()), ".15g"), v)


def _float_round_12(v: str | None) -> str | None:
    """A value that is a floating-point number -> 12 significant digits."""
    if v is None or not _NUM.match(v) or ("." not in v and "e" not in v.lower()):
        return v
    try:
        return format(float(v), ".12g")
    except ValueError:
        return v


def _integral_float(v: str | None) -> str | None:
    """2.0 -> 2 (engines disagree whether an integral REAL result is REAL or INTEGER)."""
    if v is None or not _NUM.match(v):
        return v
    try:
        f = float(v)
    except ValueError:
        return v
    if f.is_integer() and abs(f) < 2**53:
        return str(int(f))
    return v


def _float32(v: str | None) -> str | None:
    """A floating-point number -> its nearest single-precision value, 7 significant digits
    (engines where REAL is 4 bytes, e.g. DuckDB, against engines where it is 8 bytes)."""
    if v is None or not _NUM.match(v) or ("." not in v and "e" not in v.lower()):
        return v
    import struct

    try:
        f = struct.unpack("f", struct.pack("f", float(v)))[0]
    except (OverflowError, ValueError):
        return v
    return format(f, ".7g")


def _bool_int(v: str | None) -> str | None:
    """true/false -> 1/0."""
    return {"true": "1", "false": "0", "True": "1", "False": "0"}.get(v, v) if v is not None else None


NORMALIZERS: dict[str, Callable[[str | None], str | None]] = {
    "float_text_15": _float_text_15,
    "float_round_12": _float_round_12,
    "integral_float": _integral_float,
    "bool_int": _bool_int,
    "float32": _float32,
}


def make(names: list[str] | None) -> Callable[[list[tuple]], list[tuple]] | None:
    """Row normalizer applying ``names`` in order, or None for no normalization."""
    if not names:
        return None
    unknown = [n for n in names if n not in NORMALIZERS]
    if unknown:
        raise ValueError(f"unknown normalizers: {unknown}")
    fs = [NORMALIZERS[n] for n in names]

    def apply(rows: list[tuple]) -> list[tuple]:
        out = []
        for r in rows:
            vals = []
            for v in r:
                for f in fs:
                    v = f(v)
                vals.append(v)
            out.append(tuple(vals))
        return out

    return apply
