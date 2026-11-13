#!/usr/bin/env bash
# One-command reproduction of the headline result: the fuzzer finds the ten PostgreSQL bugs we
# reported that exist in the assertion-enabled base build 26bd08fb, in one 150-second run.
# The eleventh, BUG #19828, existed on master only between f8da64e6 (2 Nov 2026) and its fix
# 45ff0b4a (3 Nov 2026); REPRO_19828=1 also builds master 633dee1b from that window and runs
# its reproducer.
#
#   sudo bash scripts/reproduce.sh            # Ubuntu 22.04/24.04, run from the repository root
#
# Steps: (1) system packages; (2) build PostgreSQL 26bd08fb with assertions into
# $ROOT/install/base (skipped if it exists; about 10 min on 4 cores); (3) Python dependencies;
# (4) one server on port 5460 as the unprivileged user 'pg' (created if missing; initdb refuses
# root); (5) one fuzzing trial of the Grammar+Oracles configuration for $SECONDS_BUDGET seconds;
# (6) the list of known bugs the trial reproduced (expected: 10 of 10); (7, optional) BUG #19828. Needs root or sudo for
# steps 1 and 4. Variables: ROOT (default $HOME/pgfuzz), SECONDS_BUDGET (default 150),
# REPRO_19828 (default 0).
# The assertion crashes are expected (they are the bugs). After one of them the server may fail
# to restart because of a known upstream crash-recovery bug (PostgreSQL BUG #17731, "could not
# create file ... File exists"); the trial still records every bug found before that.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
ROOT=${ROOT:-$HOME/pgfuzz}
BASE=26bd08fb
BUDGET=${SECONDS_BUDGET:-150}
SUDO=""; [ "$(id -u)" = 0 ] || SUDO=sudo

echo "== 1/6 system packages"
$SUDO apt-get install -y build-essential bison flex libreadline-dev zlib1g-dev libssl-dev libicu-dev \
  libxml2-dev pkg-config git python3-pip >/dev/null 2>&1 || echo "(apt-get skipped; make sure the build tools are installed)"

echo "== 2/6 PostgreSQL $BASE (assertions on) -> $ROOT/install/base"
if [ ! -x "$ROOT/install/base/bin/postgres" ]; then
  mkdir -p "$ROOT/src"
  [ -d "$ROOT/src/postgres-base" ] || git clone --filter=blob:none https://github.com/postgres/postgres.git "$ROOT/src/postgres-base"
  ( cd "$ROOT/src/postgres-base" && git checkout -q "$BASE" \
    && CFLAGS="-O1 -g -fno-omit-frame-pointer" ./configure --prefix="$ROOT/install/base" \
         --enable-debug --enable-cassert --enable-tap-tests=no --with-libxml >/dev/null \
    && make -s -j"$(nproc)" && make -s install )
fi
"$ROOT/install/base/bin/postgres" --version

echo "== 3/6 Python dependencies"
python3 -m pip install -q -r "$REPO/src/requirements.txt" 2>/dev/null \
  || python3 -m pip install -q --break-system-packages -r "$REPO/src/requirements.txt"

echo "== 4/6 server on port 5460 (user pg)"
id pg >/dev/null 2>&1 || $SUDO useradd -m pg
export PGBIN="$ROOT/install/base/bin"
DATA=/home/pg/rd-0      # path fixed by configs/rediscover.yaml (server_log); recreated on every run
$SUDO env PGBIN="$PGBIN" bash "$REPO/scripts/rediscover_servers.sh" stop 1 >/dev/null 2>&1 || true
$SUDO rm -rf "${DATA:?}"
$SUDO env PGBIN="$PGBIN" bash "$REPO/scripts/rediscover_servers.sh" start 1

echo "== 5/6 one fuzzing trial, $BUDGET s"
cd "$REPO/src"
python3 - "$BUDGET" <<'PY'
import sys, yaml
raw = yaml.safe_load(open("configs/rediscover.yaml"))
raw.update({"experiment": "reproduce", "trials": 1, "budget": {"seconds": int(sys.argv[1])}})
# one short run instead of 4 x 30 min: replay the bug seeds a little more often (5% instead
# of 2%) and in turn rather than at random, so that each is replayed in the budget
raw["configs"][0]["generator"]["params"].update({"seed_prob": 0.05, "seed_cycle": True})
open("configs/.reproduce.yaml", "w").write(yaml.safe_dump(raw, sort_keys=False))
PY
python3 -m pgfuzz -q run configs/.reproduce.yaml -j 1 --fresh --no-report || true
rm -f configs/.reproduce.yaml

echo "== 6/6 result"
python3 - <<'PY'
import glob, json
sums = sorted(glob.glob("results/reproduce/*/trial-*/summary.json"))
if not sums:
    raise SystemExit("no trial summary found (see src/results/reproduce)")
s = json.load(open(sums[-1]))
found = sorted(s.get("known_bugs_reproduced") or [])
import yaml
total = len(yaml.safe_load(open("known_bugs/known_bugs.yaml"))["bugs"])
print(f"Known bugs reproduced: {len(found)} of {total}")
for b in found:
    print("  -", b)
PY
$SUDO env PGBIN="$PGBIN" bash "$REPO/scripts/rediscover_servers.sh" stop 1 >/dev/null 2>&1 || true

if [ "${REPRO_19828:-0}" = 1 ]; then
  echo "== 7/7 BUG #19828 on master 633dee1b (between f8da64e6 and the fix 45ff0b4a)"
  M=633dee1bd1b41145f81619423d573754c7ad2b9e
  if [ ! -x "$ROOT/install/m19828/bin/postgres" ]; then
    mkdir -p "$ROOT/src/postgres-19828"
    ( cd "$ROOT/src/postgres-19828" && { [ -d .git ] || git init -q; } \
      && { git remote get-url origin >/dev/null 2>&1 || git remote add origin https://github.com/postgres/postgres.git; } \
      && git fetch -q --depth 1 origin "$M" && git checkout -q FETCH_HEAD \
      && ./configure --prefix="$ROOT/install/m19828" --enable-cassert --without-icu >/dev/null \
      && make -s -j"$(nproc)" && make -s install )
  fi
  D=/home/pg/m19828
  $SUDO rm -rf "${D:?}"
  $SUDO su pg -c "$ROOT/install/m19828/bin/initdb -D $D -U postgres -A trust >/dev/null"
  $SUDO su pg -c "$ROOT/install/m19828/bin/pg_ctl -D $D -o '-p 5470 -k /tmp' -l $D/log -w start >/dev/null"
  OUT=$("$ROOT/install/m19828/bin/psql" -X -h /tmp -p 5470 -U postgres -f "$REPO/docs/bughunt/new/E-02-memoize-subplan-param.sql" 2>&1 || true)
  $SUDO su pg -c "$ROOT/install/m19828/bin/pg_ctl -D $D -m fast -w stop >/dev/null" || true
  if echo "$OUT" | grep -q "plan should not reference subplan's variable"; then
    echo "BUG #19828 reproduced: ERROR: plan should not reference subplan's variable (400 rows with enable_memoize = off)"
  else
    echo "BUG #19828 NOT reproduced; psql output:"; echo "$OUT" | tail -5
  fi
fi
