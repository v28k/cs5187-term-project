#!/usr/bin/env bash
# Build an instrumented PostgreSQL without Docker and without root.
#
#   PG_REF=master bash harness/local/build_pg.sh            # assert-enabled master (bug hunting)
#   PG_REF=REL_18_STABLE COVERAGE=1 bash harness/local/build_pg.sh   # coverage build (experiments)
#
# Environment variables (all optional):
#   PG_REF      git branch/tag to build                  (default: master)
#   PG_REPO     git URL                                  (default: https://github.com/postgres/postgres.git)
#   ROOT        working directory                        (default: $HOME/pgfuzz)
#   PREFIX      install prefix                           (default: $ROOT/install/<PG_REF>[-cov|-asan])
#   CASSERT     1 = --enable-cassert (needed to see Assert failures)   (default: 1)
#   COVERAGE    1 = --enable-coverage (gcov, slower)                    (default: 0)
#   SANITIZER   none | asan | ubsan                                     (default: none)
#   JOBS        parallel make jobs                                      (default: nproc)
#
# PostgreSQL 17+ source needs bison >= 2.3 and flex >= 2.5.35. If they are not
# installed, this script builds m4, bison and flex into $ROOT/tools first.
set -euo pipefail

PG_REF=${PG_REF:-master}
PG_REPO=${PG_REPO:-https://github.com/postgres/postgres.git}
ROOT=${ROOT:-$HOME/pgfuzz}
CASSERT=${CASSERT:-1}
COVERAGE=${COVERAGE:-0}
SANITIZER=${SANITIZER:-none}
JOBS=${JOBS:-$(nproc)}
SUFFIX=""
[ "$COVERAGE" = 1 ] && SUFFIX="$SUFFIX-cov"
[ "$SANITIZER" != none ] && SUFFIX="$SUFFIX-$SANITIZER"
PREFIX=${PREFIX:-$ROOT/install/$PG_REF$SUFFIX}
SRC=$ROOT/src/postgres-$PG_REF$SUFFIX
TOOLS=$ROOT/tools
export PATH="$TOOLS/bin:$PATH"

mkdir -p "$ROOT/src" "$TOOLS"
log() { echo "[build_pg] $*"; }

fetch_build() {  # name url configure-args...
  local name=$1 url=$2; shift 2
  if [ -x "$TOOLS/bin/$name" ]; then return; fi
  log "building $name into $TOOLS"
  local d; d=$(mktemp -d)
  (cd "$d" && curl -fsSL "$url" -o src.tar.gz && tar xzf src.tar.gz && cd */ \
     && ./configure --prefix="$TOOLS" "$@" >/dev/null && make -j"$JOBS" >/dev/null && make install >/dev/null)
  rm -rf "$d"
}

command -v m4 >/dev/null || fetch_build m4 https://ftp.gnu.org/gnu/m4/m4-1.4.19.tar.gz
command -v bison >/dev/null || fetch_build bison https://ftp.gnu.org/gnu/bison/bison-3.8.2.tar.gz
command -v flex >/dev/null || fetch_build flex https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz

if [ ! -d "$SRC/.git" ]; then
  log "cloning $PG_REPO ($PG_REF) into $SRC"
  git clone --depth 1 --branch "$PG_REF" "$PG_REPO" "$SRC"
else
  log "updating $SRC"
  git -C "$SRC" fetch --depth 1 origin "$PG_REF" && git -C "$SRC" reset --hard FETCH_HEAD
fi

CFG=(--prefix="$PREFIX" --enable-debug --enable-tap-tests=no)
[ "$CASSERT" = 1 ] && CFG+=(--enable-cassert)
[ "$COVERAGE" = 1 ] && CFG+=(--enable-coverage)
# Optional libraries: use them when the headers exist, otherwise build without.
[ -f /usr/include/readline/readline.h ] || CFG+=(--without-readline)
command -v pkg-config >/dev/null && pkg-config --exists icu-uc 2>/dev/null || CFG+=(--without-icu)
[ -f /usr/include/zlib.h ] || CFG+=(--without-zlib)
[ -f /usr/include/libxml2/libxml/parser.h ] && CFG+=(--with-libxml)

CFLAGS_EXTRA="-O1 -g -fno-omit-frame-pointer"
case "$SANITIZER" in
  asan)  CFLAGS_EXTRA="$CFLAGS_EXTRA -fsanitize=address"; export LDFLAGS="-fsanitize=address" ;;
  ubsan) CFLAGS_EXTRA="$CFLAGS_EXTRA -fsanitize=undefined -fno-sanitize-recover=all -fno-sanitize=alignment"
         export LDFLAGS="-fsanitize=undefined" ;;
esac
[ "$COVERAGE" = 1 ] && CFLAGS_EXTRA="-O0 -g"

cd "$SRC"
log "configure ${CFG[*]}"
CFLAGS="$CFLAGS_EXTRA" ./configure "${CFG[@]}" >"$ROOT/configure-$PG_REF$SUFFIX.log"
log "make -j$JOBS (log: $ROOT/make-$PG_REF$SUFFIX.log)"
make -j"$JOBS" >"$ROOT/make-$PG_REF$SUFFIX.log" 2>&1
make install >>"$ROOT/make-$PG_REF$SUFFIX.log" 2>&1
git rev-parse HEAD >"$PREFIX/SOURCE_COMMIT"
echo "$SRC" >"$PREFIX/SOURCE_DIR"
"$PREFIX/bin/pg_config" --configure >"$PREFIX/CONFIGURE_FLAGS"
log "installed $(git rev-parse --short HEAD) to $PREFIX"
log "next: bash harness/local/pg_local.sh init  (PG_BIN=$PREFIX/bin)"
