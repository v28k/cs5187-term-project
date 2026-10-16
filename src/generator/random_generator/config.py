"""Configuration for the random/mutation generator (matches eval/configs/random.yaml)."""

from dataclasses import dataclass


@dataclass
class RandomGeneratorConfig:
    seed: int = 42                  # RNG seed, for reproducibility
    min_mutations: int = 1          # min mutations applied per generated query
    max_mutations: int = 4          # max mutations applied per generated query
    pure_random_fraction: float = 0.05
    # fraction of outputs that are pure random-byte strings rather than
    # mutated seeds -- keeps a slice of "classic" unstructured fuzzing
    # in the mix, as a sanity baseline within the baseline.
    pure_random_length_range: tuple = (5, 60)
