#!/bin/bash
cd ~/audit/fuzz
for s in "$@"; do
  ~/pgfuzz/venv/bin/python ptfuzz.py 5460 $s 400 > log-pt-$s.txt 2>&1 &
done
wait
tail -n 1 log-pt-*.txt
ls out-pt 2>/dev/null | head -20
grep -c TRAP ~/audit/data/m1/server.log || true
