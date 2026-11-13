"""Overlay miner (A3): draft ``%drop`` lines from measured per-alternative validity.

After a ``sample --execute`` run the grammar generator knows, for every top-level grammar
alternative, how often a statement containing it was generated (``alt_use``) and how often that
statement executed without error (``alt_ok``). An alternative that is used often and almost
never succeeds is a dialect gap of the engine. The miner turns each such alternative into an
overlay directive ``%drop rule "<text>"`` where ``<text>`` is the shortest prefix of the
alternative's source text that selects it alone among the rule's alternatives. The draft is
meant to be re-measured (apply it, sample again) and reviewed; alternatives that fail only
because a child is broken are left for the next round, so mining is iterative. Two guards keep
the miner from blaming parents for their children: the start rule is never mined, and neither
is a rule whose measured alternatives all fail (then the cause is in a shared child).
"""

from __future__ import annotations

import re
import shlex
from typing import Any


def _alt_text(text: str, alt: Any) -> str:
    a, b = alt.span
    return text[a:b]


def _unique_key(own: str, others: list[str]) -> str:
    """Shortest prefix of ``own`` (cut at whitespace, raw source text, as ``%drop`` matches it)
    that no other alternative of the rule contains; "" if there is none."""
    cuts = [m.start() for m in re.finditer(r"\s+", own)] + [len(own)]
    for c in cuts:
        key = own[:c].strip()
        if key and "\n" not in key and not any(key in o for o in others):
            return key
    return ""


def mine(gen: Any, min_uses: int = 20, max_ok: float = 0.1) -> list[dict[str, Any]]:
    """Alternatives used >= ``min_uses`` times with ok rate <= ``max_ok``, worst first."""
    text = getattr(gen, "grammar_text", "") or ""
    out = []
    for rule, variants in gen.grammar.rules.items():
        alts = [a for v in variants for a in v.alts]
        texts = {a.uid: _alt_text(text, a) for a in alts} if text else {}
        measured = [a for a in alts if gen.alt_use.get(a.uid, 0) >= min_uses]
        if rule == gen.grammar.start or (measured and all(
                gen.alt_ok.get(a.uid, 0) / gen.alt_use[a.uid] <= max_ok for a in measured)):
            continue        # every alternative fails: the cause is below (a child), not here
        for a in alts:
            n = gen.alt_use.get(a.uid, 0)
            if n < min_uses:
                continue
            rate = gen.alt_ok.get(a.uid, 0) / n
            if rate > max_ok:
                continue
            own = texts.get(a.uid, "")
            key = _unique_key(own, [t for u, t in texts.items() if u != a.uid]) if own else ""
            out.append({"rule": rule, "line": a.line, "uses": n, "ok_rate": round(rate, 3),
                        "text": re.sub(r"\s+", " ", own).strip(), "key": key})
    out.sort(key=lambda d: (d["ok_rate"], -d["uses"]))
    return out


def render_overlay(found: list[dict[str, Any]], engine: str = "") -> str:
    lines = [f"# Mined overlay draft{' for ' + engine if engine else ''} (pgfuzz sample --mine-overlay).",
             "# Each line: an alternative that almost never executes on this engine. Review, apply with",
             "# generator.params.overlays, sample again, and repeat until validity stops improving.", ""]
    for d in found:
        lines.append(f"# line {d['line']}: ok {d['ok_rate']:.0%} of {d['uses']} uses: {d['text'][:100]}")
        if d["key"]:
            lines.append(f"%drop {d['rule']} {shlex.quote(d['key'])}")
        else:
            lines.append(f"# (no unique key; edit by hand) %drop {d['rule']} ...")
    return "\n".join(lines) + "\n"
