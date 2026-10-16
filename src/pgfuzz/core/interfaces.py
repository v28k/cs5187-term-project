"""Plug-in interfaces.

Member A implements :class:`Executor` (instrumented PostgreSQL + Docker harness).
Member B implements :class:`Generator` (random/mutation baseline, grammar generator).
The LLM-guided generator of later stages is just another :class:`Generator`.

Plug-ins are referenced from experiment configs as ``"package.module:ClassName"``
and constructed with the ``params`` mapping from the config as keyword arguments.
"""

from __future__ import annotations

import abc
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pgfuzz.core.types import CoverageSample, ExecResult, Outcome, TestCase


@dataclass
class GeneratorContext:
    """Everything a generator may depend on. Generators must draw all randomness
    from ``rng`` so that a trial is reproducible from its seed."""

    seed: int
    rng: random.Random
    workdir: Path
    trial: int = 0
    config_name: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Feedback:
    """What the runner tells a generator after each test case. Guided generators
    (grammar + coverage, grammar + LLM) use this to prioritise exploration."""

    testcase: TestCase
    result: ExecResult
    outcome: Outcome
    statement_outcomes: list[Outcome]
    new_features: frozenset[str]
    new_signature: bool
    coverage: CoverageSample | None = None


class Generator(abc.ABC):
    name: str = "generator"

    def setup(self, ctx: GeneratorContext) -> None:
        """Called once per trial before the first ``next_testcase``."""
        self.ctx = ctx

    @abc.abstractmethod
    def next_testcase(self) -> TestCase | None:
        """Return the next test case, or ``None`` when the generator is exhausted."""

    def feedback(self, fb: Feedback) -> None:
        """Optional: receive execution feedback. Unguided baselines ignore it."""

    def describe(self) -> dict[str, Any]:
        """Version / parameters recorded in the run manifest."""
        return {"name": self.name}

    def close(self) -> None:
        pass


class Executor(abc.ABC):
    name: str = "executor"

    def start(self) -> None:
        """Bring the target up (connect, start container, ...)."""

    def stop(self) -> None:
        """Tear the target down. Must be safe to call twice."""

    @abc.abstractmethod
    def execute(self, testcase: TestCase) -> ExecResult:
        """Run every statement of ``testcase`` and report raw results.

        Contract:
        * one :class:`StatementResult` per statement, in order;
        * an error in one statement must not stop later statements (unless the
          connection is gone, in which case the rest are ``SKIPPED``);
        * database state must not leak between test cases (or the leak must be
          documented in ``describe()``);
        * after a crash the executor recovers on its own before returning.
        """

    def sample_coverage(self) -> CoverageSample | None:
        """Return current cumulative coverage, or ``None`` if not instrumented.
        Called every ``coverage_interval_s`` seconds, never per test case."""
        return None

    def describe(self) -> dict[str, Any]:
        """Server version, build flags, isolation mode, ... for the run manifest."""
        return {"name": self.name}

    def __enter__(self) -> "Executor":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()
