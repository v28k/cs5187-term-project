#!/usr/bin/env bash
# Find the PostgreSQL commit that introduced a bug, with git bisect.
#
#   bash scripts/bisect_pg.sh GOOD_REF BAD_REF REPRO.sql MODE [EXPECTED.out]
#
#   GOOD_REF   a commit/tag where the bug is absent (e.g. REL_16_STABLE, a release tag)
#   BAD_REF    a commit where it is present (e.g. master)
#   REPRO.sql  the reduced test case (e.g. results/triage/<sig>/reduced.sql)
#   MODE       crash     : bad if the backend crashes or an assertion fails
#              error     : bad if psql reports an ERROR (internal errors)
#              output    : bad if psql's output differs from EXPECTED.out
#              differ    : bad if the last two queries of REPRO.sql return different rows
#                          (differential / metamorphic candidates: reduced.sql ends
#                          with the two queries that must agree)
#
# Environment: PG_SRC (a full-history clone; default $HOME/pgfuzz/src/postgres-bisect),
# JOBS (default nproc), PORT (default 5499). Each step builds into a scratch prefix;
# commits that do not build are skipped (exit 125). Must not run as root (initdb).
set -euo pipefail
GOOD=$1 BAD=$2 REPRO=$(realpath "$3") MODE=$4 EXPECTED=${5:+$(realpath "$5")}
PG_SRC=${PG_SRC:-$HOME/pgfuzz/src/postgres-bisect}
JOBS=${JOBS:-$(nproc)}
PORT=${PORT:-5499}
WORK=$(mktemp -d)
SCHEMA=$(realpath "$(dirname "$0")/../src/corpus/schema.sql")

if [ ! -d "$PG_SRC/.git" ]; then
  echo "cloning full history into $PG_SRC (once)"
  git clone https://github.com/postgres/postgres.git "$PG_SRC"
fi

if [ "$MODE" = differ ]; then   # split REPRO into setup + the two queries that must agree
  PYTHONPATH="$(dirname "$0")/../src" python3 - "$REPRO" "$WORK" <<'PY'
import sys
from pgfuzz.core.sqlsplit import split_statements
stmts = split_statements(open(sys.argv[1]).read())
w = sys.argv[2]
open(f"{w}/setup.sql", "w").write("".join(s + ";\n" for s in stmts[:-2]))
open(f"{w}/q1.sql", "w").write(stmts[-2] + ";\n")
open(f"{w}/q2.sql", "w").write(stmts[-1] + ";\n")
PY
fi

cat >"$WORK/step.sh" <<STEP
#!/usr/bin/env bash
set -u
P=$WORK/inst D=$WORK/data
rm -rf "\$P" "\$D"
( ./configure --prefix="\$P" --enable-cassert --enable-debug --without-icu --enable-tap-tests=no -q >/dev/null \
  && make -s -j$JOBS >/dev/null 2>&1 && make -s install >/dev/null 2>&1 ) || exit 125
"\$P/bin/initdb" -D "\$D" -U postgres --auth=trust >/dev/null || exit 125
"\$P/bin/pg_ctl" -D "\$D" -o "-p $PORT -c fsync=off" -l "\$D/log" -w start >/dev/null || exit 125
"\$P/bin/psql" -X -h 127.0.0.1 -p $PORT -U postgres -d postgres -f "$SCHEMA" >/dev/null 2>&1 || true
PSQL="\$P/bin/psql -X -A -t -h 127.0.0.1 -p $PORT -U postgres -d postgres"
if [ "$MODE" = differ ]; then
  A=\$(\$PSQL -1 -f $WORK/setup.sql -f $WORK/q1.sql 2>&1 | sort)
  B=\$(\$PSQL -1 -f $WORK/setup.sql -f $WORK/q2.sql 2>&1 | sort)
else
  OUT=\$(\$PSQL -f "$REPRO" 2>&1)
fi
"\$P/bin/pg_ctl" -D "\$D" -m immediate stop >/dev/null 2>&1
case "$MODE" in
  crash)  grep -q "TRAP:\|terminated by signal" "\$D/log" && exit 1 || exit 0 ;;
  error)  echo "\$OUT" | grep -q "ERROR:" && exit 1 || exit 0 ;;
  output) diff -q <(echo "\$OUT") "$EXPECTED" >/dev/null && exit 0 || exit 1 ;;
  differ) [ "\$A" = "\$B" ] && exit 0 || exit 1 ;;
esac
STEP
chmod +x "$WORK/step.sh"

cd "$PG_SRC"
git bisect reset >/dev/null 2>&1 || true
git bisect start "$BAD" "$GOOD"
git bisect run "$WORK/step.sh"
git bisect log | tee "$WORK/bisect.log"
git bisect reset
echo "log: $WORK/bisect.log"
