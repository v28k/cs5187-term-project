"""`pgfuzz sample` output -> sqlite3 shell script: every test case inside BEGIN ... ROLLBACK,
as the SQLite driver runs it, so test cases do not see each other's tables."""
import sys

first = True
for line in sys.stdin:
    if line.startswith("-- testcase "):
        if not first:
            print("ROLLBACK;")
        print("BEGIN;")
        first = False
    else:
        sys.stdout.write(line)
if not first:
    print("ROLLBACK;")
