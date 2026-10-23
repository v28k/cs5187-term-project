"""Per-trial metric accumulation.

Definitions (these are the definitions to quote in the paper):

* **parse-valid rate**   statements not rejected with SQLSTATE 42601 / all executed statements.
* **valid-query rate**   statements that completed without error / all executed statements.
* **feature coverage**   distinct catalog features in parse-valid statements / catalog size.
* **feature pairs**      distinct co-occurring feature pairs in parse-valid statements.
* **query diversity**    distinct statement shapes (literals and identifiers abstracted)
                         among parse-valid statements.
* **unique bug candidates** distinct failure signatures with a bug-candidate outcome.
* **throughput**         executed statements (and test cases) per wall-clock second.
* **plan shapes**        distinct digests of plan-node trees among sampled queries
                         (only when the executor samples ``EXPLAIN`` plans).
* **time to detect**     per known bug, the first time a signature matched it.

Statements reported ``SKIPPED`` (after a connection loss) are not "executed".
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pgfuzz.core.types import CoverageSample, ExecResult, Outcome, StatementStatus, TestCase
from pgfuzz.eval.features import FEATURE_IDS, feature_pairs, features_of, statement_shape
from pgfuzz.eval.oracle import Classification
from pgfuzz.eval.signature import Signature


@dataclass
class SignatureRecord:
    id: str
    outcome: str
    strength: str
    key: str
    sqlstate: str | None
    message: str | None
    first_t: float
    first_testcase: int
    count: int = 1
    known_bugs: list[str] = field(default_factory=list)


@dataclass
class UpdateResult:
    statement_outcomes: list[Outcome]
    new_features: frozenset[str]
    new_signature: bool


class TrialMetrics:
    def __init__(self) -> None:
        self.testcases = 0
        self.statements = 0
        self.statements_parsed = 0
        self.statements_ok = 0
        self.stmt_outcomes: Counter[str] = Counter()
        self.tc_outcomes: Counter[str] = Counter()
        self.features: set[str] = set()
        self.pairs: set[tuple[str, str]] = set()
        self.shapes: set[str] = set()
        self.plan_shapes: set[str] = set()
        self.known_first_t: dict[str, float] = {}
        self.signatures: dict[str, SignatureRecord] = {}
        self.time_to_first_bug: float | None = None
        self.exec_ms = 0.0
        self.server_restarts = 0
        self.coverage: CoverageSample | None = None
        self.elapsed = 0.0

    def update(
        self,
        t: float,
        tc: TestCase,
        res: ExecResult,
        cls: Classification,
        sig: Signature | None,
        known: list[str] | None = None,
    ) -> UpdateResult:
        self.testcases += 1
        self.tc_outcomes[cls.outcome.value] += 1
        self.exec_ms += res.wall_ms
        self.server_restarts += int(res.server_restarted)

        new_features: set[str] = set()
        for sql, st, oc in zip(tc.statements, res.statements, cls.statement_outcomes):
            if st.status is StatementStatus.SKIPPED:
                continue
            self.statements += 1
            self.stmt_outcomes[oc.value] += 1
            if oc is Outcome.OK:
                self.statements_ok += 1
            if oc.parsed:
                self.statements_parsed += 1
                feats = features_of(sql)
                new_features |= feats - self.features
                self.features |= feats
                self.pairs |= feature_pairs(feats)
                self.shapes.add(hashlib.blake2b(statement_shape(sql).encode(), digest_size=8).hexdigest())
            if st.plan_shape:
                self.plan_shapes.add(st.plan_shape)

        new_sig = False
        if sig is not None and cls.is_bug_candidate:
            rec = self.signatures.get(sig.id)
            if rec is None:
                new_sig = True
                self.signatures[sig.id] = SignatureRecord(
                    id=sig.id,
                    outcome=cls.outcome.value,
                    strength=sig.strength,
                    key=sig.key,
                    sqlstate=cls.sqlstate,
                    message=cls.message,
                    first_t=round(t, 3),
                    first_testcase=tc.id,
                    known_bugs=list(known or []),
                )
                if self.time_to_first_bug is None:
                    self.time_to_first_bug = round(t, 3)
            else:
                rec.count += 1
            for k in known or []:
                self.known_first_t.setdefault(k, round(t, 3))
        return UpdateResult(cls.statement_outcomes, frozenset(new_features), new_sig)

    def snapshot(self, t: float) -> dict[str, Any]:
        snap: dict[str, Any] = {
            "t": round(t, 3),
            "testcases": self.testcases,
            "statements": self.statements,
            "parse_valid": self.statements_parsed,
            "valid": self.statements_ok,
            "features": len(self.features),
            "feature_pairs": len(self.pairs),
            "shapes": len(self.shapes),
            "plan_shapes": len(self.plan_shapes),
            "bug_candidates": len(self.signatures),
        }
        if self.coverage is not None:
            snap["coverage"] = self.coverage.to_dict()
        return snap

    def summary(self) -> dict[str, Any]:
        n = self.statements or 1
        el = self.elapsed or 1e-9
        by_kind = Counter(r.outcome for r in self.signatures.values())
        known = sorted({k for r in self.signatures.values() for k in r.known_bugs})
        out: dict[str, Any] = {
            "elapsed_s": round(self.elapsed, 3),
            "testcases": self.testcases,
            "statements": self.statements,
            "parse_valid_rate": round(self.statements_parsed / n, 6),
            "valid_query_rate": round(self.statements_ok / n, 6),
            "statements_per_s": round(self.statements / el, 3),
            "testcases_per_s": round(self.testcases / el, 3),
            "mean_exec_ms": round(self.exec_ms / max(self.testcases, 1), 3),
            "feature_coverage": round(len(self.features) / len(FEATURE_IDS), 6),
            "features": len(self.features),
            "feature_pairs": len(self.pairs),
            "query_shapes": len(self.shapes),
            "bug_candidates": len(self.signatures),
            "bug_candidates_by_outcome": dict(sorted(by_kind.items())),
            "time_to_first_bug_s": self.time_to_first_bug,
            "server_restarts": self.server_restarts,
            "known_bugs_reproduced": known,
            "known_bugs_first_t": dict(sorted(self.known_first_t.items())),
            "plan_shapes": len(self.plan_shapes),
            "statement_outcomes": dict(sorted(self.stmt_outcomes.items())),
            "testcase_outcomes": dict(sorted(self.tc_outcomes.items())),
            "features_seen": sorted(self.features),
        }
        if self.coverage is not None:
            out["coverage"] = self.coverage.to_dict()
            c = self.coverage
            if c.lines_covered is not None and c.lines_total:
                out["line_coverage"] = round(c.lines_covered / c.lines_total, 6)
            if c.branches_covered is not None and c.branches_total:
                out["branch_coverage"] = round(c.branches_covered / c.branches_total, 6)
            if c.edges is not None:
                out["edges"] = c.edges
        return out
