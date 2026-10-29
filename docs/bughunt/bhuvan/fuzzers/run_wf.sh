#!/bin/bash
cd ~/audit2/fuzz
for s in $(seq ${2:-10} ${3:-17}); do
  ~/pgfuzz/venv/bin/python winfuzz.py ${1:-5480} $s ${4:-3000} > wf_$s.log 2>&1 &
done
wait
grep -h "done\|MISMATCH\|ERROR\|LOST" wf_*.log | sort | uniq -c | sort -rn | head -40
