#!/usr/bin/env bash
# Run the cross-version join fuzzer forever, one seed per 20000 queries.
#   bash scripts/joinfuzz_loop.sh START_SEED [TEST_PORT] [REF_PORT]
cd "$(dirname "$0")/../src" || exit 1
seed=${1:-100}
while true; do
  python3 -m xversion.joinfuzz --test-port "${2:-5434}" --ref-port "${3:-5435}" -n 20000 --seed "$seed" --out results/joinfuzz | tail -n 1
  seed=$((seed + 1))
done
