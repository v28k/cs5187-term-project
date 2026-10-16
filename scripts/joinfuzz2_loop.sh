#!/usr/bin/env bash
# Run joinfuzz2 forever, one seed per 10000 queries.
#   bash scripts/joinfuzz2_loop.sh START_SEED [TEST_PORT] [REF_PORT]
cd "$(dirname "$0")/../src" || exit 1
seed=${1:-1}
setup=""
while true; do
  python3 -m xversion.joinfuzz2 --test-port "${2:-5434}" --ref-port "${3:-5435}" -n 10000 --seed "$seed" --out results/joinfuzz2 $setup | tail -n 1
  setup="--no-setup"
  seed=$((seed + 1))
done
