#!/bin/bash
# run several JSON_TABLE fuzz seeds in parallel against the master cluster
cd ~/audit/fuzz
for s in "$@"; do
  ~/pgfuzz/venv/bin/python jtfuzz.py 5460 $s 3000 > log-jt-$s.txt 2>&1 &
done
wait
cat log-jt-*.txt
ls out-jt 2>/dev/null | head -20
grep -c TRAP ~/audit/data/m1/server.log
