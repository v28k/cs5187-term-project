"""The commit-directed extension loop: commit -> proposal -> gate -> (repair) -> grammar.

For every mined commit the model is asked for a fragment and seeds; the gate
runs them on the server; a rejected proposal goes back to the model with the
gate's findings, up to ``max_rounds`` times. Accepted fragments and seeds are
written where the grammar generator picks them up (``extra_grammars`` /
``seeds`` in an experiment config), so the "grammar+llm" arm of RQ1 is the
plain grammar arm plus these files.

Every round is one line of ``ledger.jsonl`` (commit, round, tokens, cost, the
full gate report). The ledger is the record behind RQ4 and makes the loop
resumable: commits that already have a final line are skipped. In manual mode
the loop stops at the first prompt that has no response yet.
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pgfuzz.llm.client import LLMClient, NeedsManualResponse
from pgfuzz.llm.commits import CommitDigest
from pgfuzz.llm.gate import Gate
from pgfuzz.llm.prompt import commit_message, feedback_message

log = logging.getLogger(__name__)


@dataclass
class LoopResult:
    done: int = 0
    accepted: int = 0
    stopped_for: str | None = None     # prompt path when manual mode needs an answer


def _ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def extend(commits: list[CommitDigest], client: LLMClient, gate: Gate, system: str, out: str | Path,
           max_rounds: int = 3) -> LoopResult:
    out = Path(out)
    (out / "fragments").mkdir(parents=True, exist_ok=True)
    (out / "seeds").mkdir(parents=True, exist_ok=True)
    ledger = out / "ledger.jsonl"
    past = _ledger(ledger)
    finished = {r["commit"] for r in past if r.get("final")}
    gated = {(r["commit"], r["round"]): r for r in past}
    res = LoopResult()
    for c in commits:
        if c.sha in finished:
            continue
        messages: list[dict[str, Any]] = [{"role": "user", "content": commit_message(c)}]
        for r in range(max_rounds):
            key = f"{c.short}-r{r}"
            try:
                reply = client.ask(key, system, messages)
            except NeedsManualResponse as e:
                res.stopped_for = str(e)
                return res
            if (c.sha, r) in gated:          # resumed: this round was gated before (and was rejected)
                messages = messages + [{"role": "assistant", "content": json.dumps(reply.data)},
                                       {"role": "user", "content": feedback_message(gated[c.sha, r]["gate"])}]
                continue
            t0 = time.time()
            rep = gate.check(reply.data["grammar_fragment"], reply.data["seeds"], c, reply.data.get("rewrites") or [])
            final = rep.accepted or r == max_rounds - 1
            row = {"commit": c.sha, "subject": c.subject, "round": r, "final": final,
                   "accepted": rep.accepted, "model": reply.model, "usage": reply.usage,
                   "cost_usd": reply.cost_usd, "replayed": reply.cached, "gate_s": round(time.time() - t0, 1),
                   "features": reply.data["features"], "target_lines": c.stats.get("target_lines"),
                   "gate": rep.to_dict()}
            with ledger.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            log.info("%s round %d: %s", c.short, r, "accepted" if rep.accepted else "rejected")
            if rep.accepted_rewrites:                      # sound rewrites are kept even if the fragment is not
                (out / "rewrites").mkdir(exist_ok=True)
                (out / "rewrites" / f"{c.short}-r{r}.json").write_text(
                    json.dumps({"commit": c.sha, "rewrites": rep.accepted_rewrites}, indent=1), encoding="utf-8")
            for i, s in enumerate(rep.accepted_seeds):     # valid seeds are kept even if the fragment is not
                (out / "seeds" / f"{c.short}-{i}.sql").write_text(s.strip() + "\n", encoding="utf-8")
            if rep.accepted:
                if rep.accepted_fragment:
                    (out / "fragments" / f"{c.short}.pgg").write_text(
                        f"# {c.short} {c.subject}\n" + reply.data["grammar_fragment"].strip() + "\n", encoding="utf-8")
                res.accepted += 1
                break
            messages = messages + [{"role": "assistant", "content": json.dumps(reply.data)},
                                   {"role": "user", "content": feedback_message(rep.details)}]
        res.done += 1
    return res


def summarize(out: str | Path) -> dict[str, Any]:
    """RQ4 numbers from a ledger: acceptance, repair rounds, cost, validity, coverage gain."""
    rows = _ledger(Path(out) / "ledger.jsonl")
    commits: dict[str, list[dict]] = {}
    for r in rows:
        commits.setdefault(r["commit"], []).append(r)
    finals = [rs[-1] for rs in commits.values() if rs[-1].get("final")]
    accepted = [f for f in finals if f["accepted"]]
    rounds = Counter(f["round"] + 1 for f in accepted)
    tok: Counter[str] = Counter()
    for r in rows:
        tok.update(r.get("usage", {}))
    validity = [r["gate"]["validity"]["rate"] for r in rows if isinstance(r["gate"].get("validity"), dict)]
    gains = [r["gate"]["coverage"]["gain_lines"] for r in rows
             if r["accepted"] and isinstance(r["gate"].get("coverage"), dict)]
    fails: Counter[str] = Counter()
    for r in rows:
        if r["accepted"]:
            continue
        g = r["gate"]
        if g.get("parse") not in ("ok", "empty fragment (seeds only)"):
            fails["parse"] += 1
        elif isinstance(g.get("reachability"), dict) and g["reachability"]["uses"] < 5:
            fails["reachability"] += 1
        elif isinstance(g.get("validity"), dict):
            fails["validity"] += 1
        else:
            fails["coverage/seeds"] += 1
    bugs = [b for r in rows for b in r["gate"].get("bug_candidates", [])]
    rw = [x for r in rows for x in (r["gate"].get("rewrites") or [])]
    return {
        "commits": len(commits), "finished": len(finals), "accepted": len(accepted),
        "acceptance_rate": round(len(accepted) / len(finals), 3) if finals else None,
        "accepted_fragments": sum(f["gate"].get("accepted_fragment", False) for f in accepted),
        "accepted_by_round": dict(sorted(rounds.items())),
        "rounds_total": len(rows), "rejections_by_stage": dict(fails),
        "tokens": dict(tok), "cost_usd": round(sum(r.get("cost_usd", 0.0) for r in rows), 3),
        "mean_validity": round(sum(validity) / len(validity), 3) if validity else None,
        "coverage_gain_lines": sum(gains) if gains else None,
        "gate_bug_candidates": len(bugs),
        "rewrites_proposed": len(rw), "rewrites_accepted": sum(bool(x.get("accepted")) for x in rw),
        "rewrites_with_mismatch": sum(bool(x.get("mismatches")) for x in rw),
    }


def render_markdown(s: dict[str, Any]) -> str:
    lines = ["| metric | value |", "|---|---|"]
    for k, v in s.items():
        lines.append(f"| {k} | {json.dumps(v) if isinstance(v, (dict, list)) else v} |")
    return "\n".join(lines)
