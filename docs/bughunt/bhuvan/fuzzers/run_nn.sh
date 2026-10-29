#!/bin/bash
cd ~/audit2/fuzz
for s in $(seq ${2:-100} ${3:-105}); do
  ~/pgfuzz/venv/bin/python nnfuzz.py ${1:-5480} $s ${4:-150} > nn_$s.log 2>&1 &
done
wait
grep -h "done\|REPORT" nn_*.log | sed 's/after:.*//' | sort | uniq -c | sort -rn | head -40
