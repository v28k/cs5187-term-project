#!/usr/bin/env bash
# Servers for the rediscovery runs: the assert-enabled base build (26bd08fb),
# one cluster per worker on port 5460 + worker, run as the unprivileged user pg.
#   bash scripts/rediscover_servers.sh start N     # start workers 0..N-1
#   bash scripts/rediscover_servers.sh restart W   # immediate restart of worker W (hang oracle)
#   bash scripts/rediscover_servers.sh stop N
set -euo pipefail
BIN=${PGBIN:-/root/pgfuzz/install/base/bin}
DATA=${PGDATA_ROOT:-/home/pg/rd}
as_pg() { su pg -c "$*"; }
case "$1" in
  start)
    for w in $(seq 0 $(($2 - 1))); do
      d=$DATA-$w
      if [ ! -d "$d" ]; then
        as_pg "$BIN/initdb -D $d -U postgres -A trust >/dev/null"
        printf "port=%d\nlisten_addresses='127.0.0.1'\nmax_connections=20\n" $((5460 + w)) >> "$d/postgresql.conf"
      fi
      as_pg "$BIN/pg_ctl -D $d -l $d/postgresql.log -w start >/dev/null" || true
    done ;;
  restart)
    d=$DATA-$2
    as_pg "$BIN/pg_ctl -D $d -l $d/postgresql.log -m immediate -w -t 60 restart >/dev/null" ;;
  stop)
    for w in $(seq 0 $(($2 - 1))); do as_pg "$BIN/pg_ctl -D $DATA-$w -m fast -w stop >/dev/null" || true; done ;;
esac
