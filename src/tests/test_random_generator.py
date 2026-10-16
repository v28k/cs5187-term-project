"""Unit tests for the random/mutation baseline generator."""

import random
from pathlib import Path

from pgfuzz.core.interfaces import GeneratorContext

from generator.common.schema import schema_from_corpus
from generator.random_generator.config import RandomGeneratorConfig
from generator.random_generator.generator import RandomGenerator
from generator.random_generator.seeds import build_seed_queries, default_seed_corpus
from generator.random_generator import mutators


def test_seed_corpus_is_nonempty_and_valid_looking():
    seeds = default_seed_corpus()
    assert len(seeds) >= 5
    for s in seeds:
        assert s.strip().endswith(";")
        assert any(kw in s.upper() for kw in ["SELECT", "INSERT", "UPDATE", "DELETE"])


def test_generator_produces_requested_count():
    gen = RandomGenerator(config=RandomGeneratorConfig(seed=1, pure_random_fraction=0.0))
    batch = gen.generate_batch(50)
    assert len(batch) == 50
    assert all(isinstance(q, str) for q in batch)


def test_generator_is_reproducible_given_same_seed():
    gen1 = RandomGenerator(config=RandomGeneratorConfig(seed=123))
    gen2 = RandomGenerator(config=RandomGeneratorConfig(seed=123))
    assert gen1.generate_batch(30) == gen2.generate_batch(30)


def test_different_seeds_produce_different_output():
    gen1 = RandomGenerator(config=RandomGeneratorConfig(seed=1))
    gen2 = RandomGenerator(config=RandomGeneratorConfig(seed=2))
    assert gen1.generate_batch(30) != gen2.generate_batch(30)


def test_pure_random_fraction_zero_means_all_from_seeds():
    # with pure_random_fraction=0 and 0 mutations forced impossible (min>=1),
    # at least check output retains some structure (not empty)
    gen = RandomGenerator(config=RandomGeneratorConfig(seed=5, pure_random_fraction=0.0, min_mutations=0, max_mutations=0))
    batch = gen.generate_batch(10)
    seeds = set(default_seed_corpus())
    assert all(q in seeds for q in batch)


def test_each_mutator_runs_without_crashing():
    rng = random.Random(0)
    sample_queries = default_seed_corpus()
    for mutator in mutators.ALL_MUTATORS:
        for q in sample_queries:
            result = mutator(q, rng)
            assert isinstance(result, str)


def test_mutate_boundary_int_replaces_a_number():
    rng = random.Random(0)
    sql = "SELECT * FROM users WHERE age > 18;"
    mutated = mutators.mutate_boundary_int(sql, rng)
    assert mutated != sql or "18" not in sql  # should change the literal in practice


def test_corpus_seeds_name_the_shared_tables():
    schema = schema_from_corpus(Path(__file__).parents[1] / "corpus" / "schema.yaml")
    seeds = build_seed_queries(schema)
    assert len(seeds) >= 5
    assert any("FROM t0" in s for s in seeds)
    assert all("users" not in s and "orders" not in s for s in seeds)
    assert all(s.strip().endswith(";") for s in seeds)


def test_plugin_follows_the_trial_seed():
    schema = str(Path(__file__).parents[1] / "corpus" / "schema.yaml")

    def run(seed: int) -> list[str]:
        gen = RandomGenerator(schema=schema, pure_random_fraction=0.0)
        gen.setup(GeneratorContext(seed=seed, rng=random.Random(seed), workdir=Path(".")))
        return [gen.next_testcase().to_sql() for _ in range(8)]

    assert run(1) == run(1)
    assert run(1) != run(2)


def test_mutate_special_string_replaces_quoted_literal():
    rng = random.Random(0)
    sql = "SELECT * FROM orders WHERE status = 'paid';"
    mutated = mutators.mutate_special_string(sql, rng)
    assert "'paid'" not in mutated


if __name__ == "__main__":
    import pytest, sys as _sys
    _sys.exit(pytest.main([__file__, "-v"]))
