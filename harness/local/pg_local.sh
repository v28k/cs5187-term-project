#!/usr/bin/env bash
# Manage N local fuzzing servers built by build_pg.sh (no Docker, no root).
#
#   bash harness/local/pg_local.sh init  [N]     # initdb N clusters (ports BASE_PORT..BASE_PORT+N-1)
#   bash harness/local/pg_local.sh start [N]
#   bash harness/local/pg_local.sh stop  [N]
#   bash harness/local/pg_local.sh status [N]
#   bash harness/local/pg_local.sh coverage I [reset]   # JSON coverage of the build (COVERAGE=1 builds)
#   bash harness/local/pg_local.sh backtrace I REPRO.sql  # gdb backtrace in a single-user copy of server I
#   bash harness/local/pg_local.sh env                  # print paths for the experiment config
#
# Environment: PG_BIN (default: newest $ROOT/install/*/bin), ROOT (default $HOME/pgfuzz),
#              BASE_PORT (default 5432).
set -euo pipefail
ROOT=${ROOT:-$HOME/pgfuzz}
BASE_PORT=${BASE_PORT:-5432}
HERE=$(cd "$(dirname "$0")" && pwd)
if [ -z "${PG_BIN:-}" ]; then
  PG_BIN=$(ls -td "$ROOT"/install/*/bin 2>/dev/null | head -1)
fi
[ -x "$PG_BIN/postgres" ] || { echo "PG_BIN not found; run build_pg.sh or set PG_BIN" >&2; exit 1; }
export PATH="$PG_BIN:$PATH"
CMD=${1:-status}
N=${2:-1}

data() { echo "$ROOT/data/pg-$1"; }
port() { echo $((BASE_PORT + $1)); }

case "$CMD" in
  init)
    for ((i = 0; i < N; i++)); do
      d=$(data "$i")
      if [ -s "$d/PG_VERSION" ]; then echo "exists: $d"; continue; fi
      mkdir -p "$(dirname "$d")"
      initdb -D "$d" -U postgres --auth=trust --no-instructions >/dev/null
      cat "$HERE/../docker/postgresql.fuzz.conf" | sed 's/\r$//' >> "$d/postgresql.conf"
      if postgres --describe-config 2>/dev/null | grep -q '^backtrace_on_internal_error'; then
        echo "backtrace_on_internal_error = on" >> "$d/postgresql.conf"
      fi
      { echo "port = $(port "$i")"; echo "listen_addresses = 'localhost'"; echo "shared_buffers = 128MB"; } >> "$d/postgresql.conf"
      echo "initialised $d (port $(port "$i"))"
    done ;;
  start)
    for ((i = 0; i < N; i++)); do
      d=$(data "$i")
      # stderr goes to the log file, so TRAP: lines and assertion backtraces land there too.
      pg_ctl -D "$d" -l "$d/postgresql.log" -w start >/dev/null && echo "started pg-$i on port $(port "$i")"
    done ;;
  stop)
    for ((i = 0; i < N; i++)); do pg_ctl -D "$(data "$i")" -m fast stop >/dev/null 2>&1 && echo "stopped pg-$i" || true; done ;;
  status)
    for ((i = 0; i < N; i++)); do printf 'pg-%d (port %d): ' "$i" "$(port "$i")"; pg_ctl -D "$(data "$i")" status >/dev/null 2>&1 && echo running || echo stopped; done ;;
  coverage)
    src=$(dirname "$PG_BIN")/SOURCE_DIR
    SRC_DIR=${SRC_DIR:-$(cat "$src" 2>/dev/null || ls -td "$ROOT"/src/postgres-*-cov 2>/dev/null | head -1)}
    COV_STATE="$ROOT/cov-state-$N" bash "$HERE/../docker/coverage.sh" "$SRC_DIR" "${3:-collect}" ;;
  backtrace)
    POSTGRES="$PG_BIN/postgres" bash "$HERE/../docker/gdb_backtrace.sh" "$(data "$N")" "${3:?REPRO.sql}" ;;
  env)
    echo "PG_BIN=$PG_BIN"
    echo "server version: $(postgres --version)"
    echo "source commit:  $(cat "$(dirname "$PG_BIN")/SOURCE_COMMIT" 2>/dev/null || echo unknown)"
    for ((i = 0; i < N; i++)); do echo "pg-$i: port $(port "$i"), log $(data "$i")/postgresql.log"; done ;;
  *)
    sed -n '2,13p' "$0"; exit 1 ;;
esac
