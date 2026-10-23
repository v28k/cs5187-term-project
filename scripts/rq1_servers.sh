#!/usr/bin/env bash
# Coverage servers for RQ1/RQ4 (configs/rq1.yaml): N servers of ONE gcov build,
# each writing its counters to its own directory, so parallel trials do not
# mix their coverage. Worker W: port BASE_PORT+W, data $ROOT/data/cov-W,
# counters under $ROOT/gcov/wW/<build path> (GCOV_PREFIX).
#
#   COVERAGE=1 PG_REF=master bash harness/local/build_pg.sh     # once: the gcov build
#   bash scripts/rq1_servers.sh init 4
#   bash scripts/rq1_servers.sh start 4 | stop 4 | status 4
#   bash scripts/rq1_servers.sh coverage W [reset]             # JSON line (the executor's coverage_command)
#   bash scripts/rq1_servers.sh srcdir W                       # build tree as seen by worker W (diff coverage)
#
# Environment: ROOT ($HOME/pgfuzz), BASE_PORT (5450), SRC (gcov build tree,
# default $ROOT/src/postgres-master-cov), PG_BIN ($ROOT/install/master-cov/bin),
# RUN_AS (cluster owner; 'pg' when run as root).
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
ROOT=${ROOT:-$HOME/pgfuzz}
BASE_PORT=${BASE_PORT:-5450}
SRC=${SRC:-$ROOT/src/postgres-master-cov}
PG_BIN=${PG_BIN:-$ROOT/install/master-cov/bin}
CMD=${1:-status}
N=${2:-4}
if [ "$(id -u)" = 0 ] && id pg >/dev/null 2>&1; then RUN_AS=${RUN_AS:-pg}; else RUN_AS=${RUN_AS:-}; fi
as() { if [ -n "$RUN_AS" ]; then su "$RUN_AS" -s /bin/bash -c "$*"; else bash -c "$*"; fi; }
gdir() { echo "$ROOT/gcov/w$1"; }

case "$CMD" in
  init)
    for ((w = 0; w < N; w++)); do
      d=$ROOT/data/cov-$w
      g=$(gdir "$w")
      # the .gcno notes must sit next to the counters for lcov/gcov
      mkdir -p "$g" && find "$SRC/src/backend" "$SRC/src/pl/plpgsql/src" -name '*.gcno' 2>/dev/null \
        | xargs -r cp --parents -t "$g"
      [ -z "$RUN_AS" ] || chown -R "$RUN_AS" "$g"
      if [ ! -s "$d/PG_VERSION" ]; then
        mkdir -p "$d" && { [ -z "$RUN_AS" ] || chown "$RUN_AS" "$d"; }
        as "$PG_BIN/initdb -D $d -U postgres --auth=trust --no-instructions >/dev/null"
        as "sed 's/\r\$//' $HERE/harness/docker/postgresql.fuzz.conf >> $d/postgresql.conf"
        as "printf 'port = %d\nlisten_addresses = '\''localhost'\''\nshared_buffers = 64MB\n' $((BASE_PORT + w)) >> $d/postgresql.conf"
      fi
      echo "cov-$w: port $((BASE_PORT + w)), counters in $g$SRC"
    done ;;
  start)
    for ((w = 0; w < N; w++)); do
      d=$ROOT/data/cov-$w
      as "GCOV_PREFIX=$(gdir "$w") GCOV_PREFIX_STRIP=0 $PG_BIN/pg_ctl -D $d -l $d/postgresql.log -w start >/dev/null" \
        && echo "started cov-$w on $((BASE_PORT + w))"
    done ;;
  stop|status)
    for ((w = 0; w < N; w++)); do
      d=$ROOT/data/cov-$w
      if [ "$CMD" = stop ]; then as "$PG_BIN/pg_ctl -D $d -m fast stop >/dev/null 2>&1" && echo "stopped cov-$w" || true
      else printf 'cov-%d (port %d): ' "$w" $((BASE_PORT + w)); as "$PG_BIN/pg_ctl -D $d status >/dev/null 2>&1" && echo running || echo stopped; fi
    done ;;
  coverage)
    w=${2:?worker}
    COV_STATE="$ROOT/cov-state-w$w" bash "$HERE/harness/docker/coverage.sh" "$(gdir "$w")$SRC" "${3:-collect}" ;;
  srcdir)
    echo "$(gdir "${2:?worker}")$SRC" ;;
  *)
    sed -n '2,16p' "$0"; exit 1 ;;
esac
