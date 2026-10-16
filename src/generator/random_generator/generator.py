"""Random/mutation baseline, arm 1 of the three-way comparison.

A test case is a seed query, built from the shared AST so the seed itself is
valid SQL, with a few text-level mutations applied. The mutations do not know
the grammar. That is the baseline the grammar arm is compared against.

Two ways to construct it:

* From an experiment config, as ``generator.random_generator.generator:RandomGenerator``
  with ``schema`` pointing at ``corpus/schema.yaml``. Randomness comes from the
  trial (``ctx.rng``), so two trials with the same seed match and two trials
  with different seeds do not.
* Standalone, with a ``RandomGeneratorConfig``, for the original unit tests and
  ``python -m generator.random_generator.cli``. That path keeps its own RNG.

``feedback`` is ignored on purpose. This arm is the unguided baseline.
"""

from __future__ import annotations

import random
import string
from typing import Iterator, List, Optional

from pgfuzz.core.interfaces import Generator, GeneratorContext
from pgfuzz.core.types import TestCase

from generator.random_generator.config import RandomGeneratorConfig
from generator.random_generator.mutators import ALL_MUTATORS
from generator.random_generator.seeds import build_seed_queries, default_seed_corpus


class RandomGenerator(Generator):
    name = "random"

    def __init__(
        self,
        config: Optional[RandomGeneratorConfig] = None,
        seed_corpus: Optional[List[str]] = None,
        schema: Optional[str] = None,
        min_mutations: int = 1,
        max_mutations: int = 4,
        pure_random_fraction: float = 0.05,
        pure_random_length_range: tuple | list = (5, 60),
        statements: int | tuple | list = 1,
    ):
        self.schema = schema
        if config is not None:
            self.min_mutations = config.min_mutations
            self.max_mutations = config.max_mutations
            self.pure_random_fraction = config.pure_random_fraction
            self.pure_random_length_range = tuple(config.pure_random_length_range)
            self._rng: random.Random | None = random.Random(config.seed)
            self.seed_corpus = seed_corpus or default_seed_corpus()
        else:
            self.min_mutations = min_mutations
            self.max_mutations = max_mutations
            self.pure_random_fraction = pure_random_fraction
            self.pure_random_length_range = tuple(pure_random_length_range)
            self._rng = None
            self.seed_corpus = seed_corpus
        lo, hi = (statements, statements) if isinstance(statements, int) else tuple(statements)
        if lo < 1 or hi < lo:
            raise ValueError("statements must be a positive range")
        self.statements = (lo, hi)
        if self.seed_corpus is not None and not self.seed_corpus:
            raise ValueError("seed_corpus must contain at least one seed query")

    def setup(self, ctx: GeneratorContext) -> None:
        super().setup(ctx)
        self._rng = ctx.rng
        if self.seed_corpus is None:
            if self.schema:
                from generator.common.schema import schema_from_corpus
                self.seed_corpus = build_seed_queries(schema_from_corpus(self.schema))
            else:
                self.seed_corpus = default_seed_corpus()

    @property
    def rng(self) -> random.Random:
        if self._rng is None:
            raise RuntimeError("setup() has not been called")
        return self._rng

    def _pure_random_string(self) -> str:
        lo, hi = self.pure_random_length_range
        length = self.rng.randint(lo, hi)
        alphabet = string.ascii_letters + string.digits + " ()'\";,.*=<>-_"
        return "".join(self.rng.choice(alphabet) for _ in range(length))

    def generate_one(self) -> str:
        """Generate a single candidate query string."""
        if self.rng.random() < self.pure_random_fraction:
            return self._pure_random_string()

        candidate = self.rng.choice(self.seed_corpus)
        n_mutations = self.rng.randint(self.min_mutations, self.max_mutations)
        for _ in range(n_mutations):
            mutator = self.rng.choice(ALL_MUTATORS)
            candidate = mutator(candidate, self.rng)
        return candidate

    def generate(self, n: int) -> Iterator[str]:
        for _ in range(n):
            yield self.generate_one()

    def generate_batch(self, n: int) -> List[str]:
        return list(self.generate(n))

    def next_testcase(self) -> TestCase | None:
        n = self.rng.randint(*self.statements)
        statements = [self.generate_one().strip().rstrip(";") for _ in range(n)]
        return TestCase(statements, origin=self.name, meta={"arm": "random"})

    def feedback(self, fb) -> None:
        """Unguided baseline: a new feature or a new bug does not steer the next case."""

    def describe(self) -> dict:
        return {
            "name": self.name,
            "schema": self.schema,
            "seeds": None if self.seed_corpus is None else len(self.seed_corpus),
            "min_mutations": self.min_mutations,
            "max_mutations": self.max_mutations,
            "pure_random_fraction": self.pure_random_fraction,
            "guided": False,
        }
