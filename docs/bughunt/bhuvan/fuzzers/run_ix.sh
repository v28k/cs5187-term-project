#!/bin/bash
cd ~/audit/fuzz
for s in "$@"; do
  ~/pgfuzz/venv/bin/python ixfuzz.py 5460 $s 300 > log-ix-$s.txt 2>&1 &
done
wait
tail -n 1 log-ix-*.txt
ls out-ix 2>/dev/null | head -20
grep -c TRAP ~/audit/data/m1/server.log || true
