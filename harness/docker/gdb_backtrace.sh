#!/usr/bin/env bash
# Get a symbolized C backtrace for a crash (SIGSEGV, SIGABRT, ...) without core dumps
# or ptrace permissions: copy the data directory, run the SQL in a single-user
# backend under gdb, and print the backtrace of the crashing thread.
#
#   gdb_backtrace.sh DATA_DIR REPRO.sql [DBNAME]
#
# Single-user mode has no parallel workers; if the crash only happens in a
# parallel worker, set max_parallel_workers_per_gather = 0 first to check, or
# attach gdb to the worker instead.
set -euo pipefail
DATA=${1:?usage: gdb_backtrace.sh DATA_DIR REPRO.sql [DBNAME]}
SQL=${2:?usage: gdb_backtrace.sh DATA_DIR REPRO.sql [DBNAME]}
DB=${3:-postgres}
POSTGRES=${POSTGRES:-$(command -v postgres)}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cp -a "$DATA" "$TMP/data"
rm -f "$TMP/data/postmaster.pid"

# In single-user mode with -j, a statement ends with a semicolon followed by an empty line.
sed 's/\r$//' "$SQL" | awk '{ print } /;[[:space:]]*$/ { print "" }' > "$TMP/input.sql"

gdb -q -batch \
    -ex "set pagination off" \
    -ex "handle SIGUSR1 nostop noprint pass" \
    -ex "handle SIGUSR2 nostop noprint pass" \
    -ex "handle SIGPIPE nostop noprint pass" \
    -ex "run < $TMP/input.sql" \
    -ex "echo \n===== BACKTRACE =====\n" \
    -ex "bt 40" \
    -ex "echo ===== END =====\n" \
    --args "$POSTGRES" --single -j -D "$TMP/data" "$DB" 2>&1 \
  | sed -n '/===== BACKTRACE =====/,/===== END =====/p'
