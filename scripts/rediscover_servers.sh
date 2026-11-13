#!/usr/bin/env bash
# Servers for the rediscovery runs: the assert-enabled base build (26bd08fb),
# one cluster per worker on port 5460 + worker, run as the unprivileged user pg.
#   bash scripts/rediscover_servers.sh start N     # start workers 0..N-1
#   bash scripts/rediscover_servers.sh restart W   # immediate restart of worker W (hang oracle,
#                                                  # failed crash recovery: new cluster)
#   bash scripts/rediscover_servers.sh stop N
set -euo pipefail
BIN=${PGBIN:-/root/pgfuzz/install/base/bin}
DATA=${PGDATA_ROOT:-/home/pg/rd}
as_pg() { su pg -c "$*"; }
init() {
  as_pg "$BIN/initdb -D $DATA-$1 -U postgres -A trust >/dev/null"
  printf "port=%d\nlisten_addresses='127.0.0.1'\nmax_connections=20\n" $((5460 + $1)) >> "$DATA-$1/postgresql.conf"
}
case "$1" in
  start)
    for w in $(seq 0 $(($2 - 1))); do
      d=$DATA-$w
      [ -d "$d" ] || init "$w"
      as_pg "$BIN/pg_ctl -D $d -l $d/postgresql.log -w start >/dev/null" || true
    done ;;
  restart)
    d=$DATA-$2
    if ! as_pg "$BIN/pg_ctl -D $d -l $d/postgresql.log -m immediate -w -t 60 restart >/dev/null"; then
      # crash recovery can fail after an assertion crash (BUG #17731, "could not create file
      # ... File exists"); start from a new cluster, the fuzzer recreates its schema
      as_pg "$BIN/pg_ctl -D $d -m immediate -w stop >/dev/null" || true
      mv "$d/postgresql.log" "$d.failed-recovery.log" 2>/dev/null || true
      rm -rf "$d"; init "$2"
      as_pg "$BIN/pg_ctl -D $d -l $d/postgresql.log -w start >/dev/null"
    fi ;;
  stop)
    for w in $(seq 0 $(($2 - 1))); do as_pg "$BIN/pg_ctl -D $DATA-$w -m fast -w stop >/dev/null" || true; done ;;
esac
