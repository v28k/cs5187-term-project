#!/usr/bin/env bash
# The release reference server for the cross-version oracle: REL_18_STABLE on port 5435.
#   bash scripts/ref_server.sh init | start | stop | status
# Environment: PGFUZZ_ROOT ($HOME/pgfuzz), PORT (5435), RUN_AS ('pg' when run as root).
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
ROOT=${PGFUZZ_ROOT:-$HOME/pgfuzz}
BIN=${PG_BIN:-$ROOT/install/REL_18_STABLE/bin}
D=$ROOT/data/ref-18
PORT=${PORT:-5435}
if [ "$(id -u)" = 0 ] && id pg >/dev/null 2>&1; then RUN_AS=${RUN_AS:-pg}; else RUN_AS=${RUN_AS:-}; fi
as() { if [ -n "$RUN_AS" ]; then su "$RUN_AS" -s /bin/bash -c "$*"; else bash -c "$*"; fi; }
case "${1:-status}" in
  init)
    [ -s "$D/PG_VERSION" ] && { echo "exists: $D"; exit 0; }
    mkdir -p "$D" && { [ -z "$RUN_AS" ] || chown "$RUN_AS" "$D"; }
    as "$BIN/initdb -D $D -U postgres --auth=trust --no-instructions >/dev/null"
    as "sed 's/\r\$//' $HERE/harness/docker/postgresql.fuzz.conf >> $D/postgresql.conf"
    as "printf 'port = %d\nlisten_addresses = '\''localhost'\''\nshared_buffers = 128MB\n' $PORT >> $D/postgresql.conf"
    echo "initialised $D (port $PORT)" ;;
  start)  as "$BIN/pg_ctl -D $D -l $D/postgresql.log -w start >/dev/null" && echo "started REL_18 on $PORT" ;;
  stop)   as "$BIN/pg_ctl -D $D -m fast stop >/dev/null" && echo stopped ;;
  status) as "$BIN/pg_ctl -D $D status >/dev/null 2>&1" && echo "running on $PORT" || echo stopped ;;
  *) sed -n '2,4p' "$0"; exit 1 ;;
esac
