#!/bin/bash
cd ~/audit/fuzz
for f in log-ix-*.txt; do echo "$f: $(tail -c 200 "$f")"; done
echo "mismatch files: $(ls out-ix 2>/dev/null | wc -l)"
echo "running workers: $(pgrep -fc '[i]xfuzz.py')"
