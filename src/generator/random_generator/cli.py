"""
Command-line entry point for the random/mutation baseline generator.

Usage:
    python -m generator.random_generator.cli --count 100 --out corpus/generated/random_batch.sql
    python -m generator.random_generator.cli --count 20 --seed 7
"""

from __future__ import annotations
import argparse
import sys

from generator.random_generator.config import RandomGeneratorConfig
from generator.random_generator.generator import RandomGenerator


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Random/mutation-based SQL query generator (baseline).")
    parser.add_argument("--count", type=int, default=20, help="number of queries to generate")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    parser.add_argument("--min-mutations", type=int, default=1)
    parser.add_argument("--max-mutations", type=int, default=4)
    parser.add_argument("--pure-random-fraction", type=float, default=0.05)
    parser.add_argument("--out", type=str, default=None, help="file to write generated queries to (one per line); defaults to stdout")
    args = parser.parse_args(argv)

    config = RandomGeneratorConfig(
        seed=args.seed,
        min_mutations=args.min_mutations,
        max_mutations=args.max_mutations,
        pure_random_fraction=args.pure_random_fraction,
    )
    gen = RandomGenerator(config=config)
    queries = gen.generate_batch(args.count)

    output = "\n".join(queries)
    if args.out:
        with open(args.out, "w") as f:
            f.write(output + "\n")
        print(f"Wrote {len(queries)} queries to {args.out}", file=sys.stderr)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
