#!/usr/bin/env bash
# Build the RQ3 server: PostgreSQL master at BASE with the fixes listed in
# src/bench/reinjected/commits.txt reverted (the bugs re-injected).
#
#   BASE=<sha> bash scripts/build_reinjected.sh
#
#   SRC     PostgreSQL git checkout       (default: $HOME/pgfuzz/src/postgres-master)
#   BASE    revision to start from        (default: the base recorded in bugs.yaml)
#   WT      worktree to build in          (default: $HOME/pgfuzz/src/reinject-wt)
#   PREFIX  install prefix                (default: $HOME/pgfuzz/install/reinjected)
#   COVERAGE=1 adds --enable-coverage (for diff coverage of the injected code)
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
SRC=${SRC:-$HOME/pgfuzz/src/postgres-master}
BASE=${BASE:-$(awk '/^base:/ {print $2}' "$HERE/src/bench/reinjected/bugs.yaml")}
WT=${WT:-$HOME/pgfuzz/src/reinject-wt}
PREFIX=${PREFIX:-$HOME/pgfuzz/install/reinjected}
JOBS=${JOBS:-$(nproc)}
EXTRA=""
[ "${COVERAGE:-0}" = 1 ] && EXTRA="--enable-coverage"

git -C "$SRC" cat-file -e "$BASE^{commit}" || git -C "$SRC" fetch origin
if [ -d "$WT" ]; then git -C "$WT" checkout -q --detach "$BASE" && git -C "$WT" reset -q --hard && git -C "$WT" clean -qfdx
else git -C "$SRC" worktree add -q --detach "$WT" "$BASE"; fi
cd "$WT"
for c in $(grep -v '^#' "$HERE/src/bench/reinjected/commits.txt"); do
  git -c user.name=pgfuzz -c user.email=pgfuzz@localhost revert --no-edit "$c" >/dev/null \
    || { echo "revert of $c does not apply on $BASE" >&2; exit 1; }
  echo "reverted $(git log -1 --format='%h %s' "$c")"
done
./configure --prefix="$PREFIX" --enable-debug --enable-cassert --with-libxml $EXTRA >/dev/null
make -j"$JOBS" -s >/dev/null
make -s install >/dev/null
echo "installed into $PREFIX ($(git rev-parse --short HEAD) = $BASE + $(git rev-list --count "$BASE"..HEAD) reverts)"
