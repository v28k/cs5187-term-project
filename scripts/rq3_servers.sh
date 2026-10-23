#!/usr/bin/env bash
# Servers for RQ3 (re-injected bugs). One config (configs/rq3.yaml) reaches all of
# them: worker W listens on port BASE_PORT+W, data in $ROOT/data/rq3-W.
#
#   W = 0..N-1     fuzzing servers: base + every fix in commits.txt reverted
#   W = 20         the fixed reference: base itself
#   W = 21 + i     "solo" server for bug i (base + only that one revert), used to
#                  check each PoC in isolation and to attribute fuzzer findings
#
#   bash scripts/rq3_servers.sh build-solo        # base install + one postgres binary per bug
#   bash scripts/rq3_servers.sh init  [N]         # initdb (needs the installs)
#   bash scripts/rq3_servers.sh start [N] | stop [N] | status [N]
#
# Run build_reinjected.sh first (it creates the worktree). Environment: ROOT
# ($HOME/pgfuzz), BASE_PORT (5440), RUN_AS (user that owns the clusters; default
# 'pg' when run as root, since initdb refuses to run as root).
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
ROOT=${ROOT:-${PGFUZZ_ROOT:-$HOME/pgfuzz}}
BASE_PORT=${BASE_PORT:-5440}
SRC=${SRC:-$ROOT/src/postgres-master}
SOLO_WT=${SOLO_WT:-$ROOT/src/solo-wt}
BASE=${BASE:-$(awk '/^base:/ {print $2}' "$HERE/src/bench/reinjected/bugs.yaml")}
JOBS=${JOBS:-$(nproc)}
INJ=$ROOT/install/reinjected
FIX=$ROOT/install/base
SOLO=$ROOT/install/solo
CMD=${1:-status}
N=${2:-4}
COMMITS=$(grep -v '^#' "$HERE/src/bench/reinjected/commits.txt")
if [ "$(id -u)" = 0 ] && id pg >/dev/null 2>&1; then RUN_AS=${RUN_AS:-pg}; else RUN_AS=${RUN_AS:-}; fi
as() { if [ -n "$RUN_AS" ]; then su "$RUN_AS" -s /bin/bash -c "$*"; else bash -c "$*"; fi; }

workers() {  # every worker index with its bindir
  for ((w = 0; w < N; w++)); do echo "$w $INJ/bin"; done
  echo "20 $FIX/bin"
  local i=0
  for c in $COMMITS; do echo "$((21 + i)) $SOLO/$c/bin"; i=$((i + 1)); done
}

case "$CMD" in
  build-solo)
    if [ ! -d "$SOLO_WT" ]; then git -C "$SRC" worktree add -q --detach "$SOLO_WT" "$BASE"; fi
    cd "$SOLO_WT"
    git checkout -q --detach "$BASE" && git reset -q --hard && git clean -qfdx
    ./configure --prefix="$FIX" --enable-debug --enable-cassert --with-libxml >/dev/null
    make -j"$JOBS" -s >/dev/null && make -s install >/dev/null
    echo "base installed into $FIX"
    for c in $COMMITS; do
      git revert --no-commit "$c" >/dev/null
      make -j"$JOBS" -s -C src/backend >/dev/null
      rm -rf "$SOLO/$c" && mkdir -p "$SOLO/$c"
      cp -al "$FIX/." "$SOLO/$c/"                       # hard links: only the binary differs
      cp --remove-destination src/backend/postgres "$SOLO/$c/bin/postgres"
      git reset -q --hard "$BASE"
      echo "solo $c: $(git log -1 --format=%s "$c")"
    done
    make -j"$JOBS" -s -C src/backend >/dev/null       # leave the tree built at base
    chmod -R a+rX "$ROOT/install" ;;
  init)
    workers | while read -r w bin; do
      d=$ROOT/data/rq3-$w
      [ -s "$d/PG_VERSION" ] && { echo "exists: $d"; continue; }
      mkdir -p "$d" && { [ -z "$RUN_AS" ] || chown "$RUN_AS" "$d"; }
      as "$bin/initdb -D $d -U postgres --auth=trust --no-instructions >/dev/null"
      as "sed 's/\r\$//' $HERE/harness/docker/postgresql.fuzz.conf >> $d/postgresql.conf"
      as "printf 'port = %d\nlisten_addresses = '\''localhost'\''\nshared_buffers = 32MB\nmax_connections = 20\n' $((BASE_PORT + w)) >> $d/postgresql.conf"
      echo "initialised rq3-$w (port $((BASE_PORT + w)), $bin)"
    done ;;
  start|stop|status)
    workers | while read -r w bin; do
      d=$ROOT/data/rq3-$w
      case "$CMD" in
        start)  as "$bin/pg_ctl -D $d -l $d/postgresql.log -w start >/dev/null" && echo "started rq3-$w on $((BASE_PORT + w))" ;;
        stop)   as "$bin/pg_ctl -D $d -m fast stop >/dev/null 2>&1" && echo "stopped rq3-$w" || true ;;
        status) printf 'rq3-%d (port %d): ' "$w" $((BASE_PORT + w)); as "$bin/pg_ctl -D $d status >/dev/null 2>&1" && echo running || echo stopped ;;
      esac
    done ;;
  *)
    sed -n '2,17p' "$0"; exit 1 ;;
esac
