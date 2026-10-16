#!/usr/bin/env bash
# Start (or resume) the grammar hunt on the two local servers (ports 5432, 5433)
# in the background. Output: src/results/cloud_hunt/, log: src/results/cloud_hunt.log
#   bash scripts/cloud_hunt.sh          # resume
#   bash scripts/cloud_hunt.sh --fresh  # start over
cd "$(dirname "$0")/../src" || exit 1
mkdir -p results
nohup python3 -m pgfuzz run configs/cloud_hunt.yaml -j 2 --no-plots "$@" >> results/cloud_hunt.log 2>&1 &
echo "hunt started, pid $!"
