#!/usr/bin/env bash
# Rebuild the bug-hunt environment from scratch on a Linux box (Ubuntu 24.04 tested).
# Needs: sudo/root for apt and for creating the unprivileged 'pg' user (initdb refuses root).
#   bash scripts/setup_env.sh        # ~25 min on 4 cores
set -euo pipefail
ROOT=${ROOT:-$HOME/pgfuzz}
sudo apt-get install -y build-essential bison flex libreadline-dev zlib1g-dev libssl-dev libicu-dev libxml2-dev gdb git python3-pip pdftotext 2>/dev/null || true
mkdir -p "$ROOT/src" && cd "$ROOT/src"
[ -d postgres-master ] || git clone --depth 3000 --branch master https://github.com/postgres/postgres.git postgres-master
[ -d postgres-REL_18_STABLE ] || git clone --depth 1 --branch REL_18_STABLE https://github.com/postgres/postgres.git postgres-REL_18_STABLE
# assert-enabled master (test side)
( cd postgres-master && CFLAGS="-O1 -g -fno-omit-frame-pointer" ./configure --prefix="$ROOT/install/master" \
    --enable-debug --enable-cassert --enable-tap-tests=no --with-libxml >/dev/null && make -s -j"$(nproc)" && make -s install )
# plain release build (reference side)
( cd postgres-REL_18_STABLE && ./configure --prefix="$ROOT/install/REL_18_STABLE" --without-icu --enable-tap-tests=no CFLAGS=-O2 >/dev/null \
    && make -s -j"$(nproc)" && make -s install )
pip install -r "$(dirname "$0")/../src/requirements.txt"
echo "Done. Next: see docs/bughunt/HANDOFF.md section 'Restarting everything'."
