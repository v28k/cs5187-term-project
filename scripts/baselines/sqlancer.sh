#!/usr/bin/env bash
# E2: SQLancer baseline under the same time budget as our arms.
#
#   scripts/baselines/sqlancer.sh build                       # clone + mvn package (once)
#   scripts/baselines/sqlancer.sh run <dbms> <oracle> <seconds> <trial>
#       dbms   : sqlite3 | duckdb | postgres (needs a server: PGHOST/PGPORT/PGUSER) | datafusion (needs
#                SQLancer's DataFusion test server, see sqlancer/test/datafusion)
#       oracle : NoREC | WHERE (TLP) | QUERY_PARTITIONING | ...  (SQLancer's --oracle names per DBMS)
#   scripts/baselines/sqlancer.sh summary                     # results/baselines/sqlancer/summary.md
#
# Each run: one thread, SQLancer's seed = trial number, output in
# results/baselines/sqlancer/<dbms>-<oracle>-<trial>/ (SQLancer's logs/ directory, one .log per
# reported bug, plus stdout with throughput). Reported logs are then deduplicated and triaged with
# the same pipeline as our candidates (replay the log's statements with `pgfuzz replay`).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SQ=${SQLANCER_DIR:-$ROOT/../sqlancer}
OUT=$ROOT/results/baselines/sqlancer
SQLANCER_REF=${SQLANCER_REF:-main}
case "${1:-}" in
build)
  [ -d "$SQ" ] || git clone --depth 1 -b "$SQLANCER_REF" https://github.com/sqlancer/sqlancer "$SQ"
  ( cd "$SQ" && mvn -q package -DskipTests )
  ls "$SQ"/target/sqlancer-*.jar ;;
run)
  dbms=$2; oracle=$3; secs=$4; trial=$5
  jar=$(ls "$SQ"/target/sqlancer-*.jar | grep -v sources | head -1)
  d=$OUT/$dbms-$oracle-$trial; mkdir -p "$d"
  extra=()
  if [ "$dbms" = postgres ]; then
    extra=(--host "${PGHOST:-localhost}" --port "${PGPORT:-5432}" --username "${PGUSER:-postgres}" --password "${PGPASSWORD:-}")
  fi
  ( cd "$d" && timeout $((secs + 120)) java -jar "$jar" --num-threads 1 --random-seed "$trial" \
      --timeout-seconds "$secs" --num-tries 1000000 "${extra[@]}" "$dbms" --oracle "$oracle" \
      > stdout.txt 2>&1 || true )
  echo "$d: $(find "$d/logs" -name '*.log' 2>/dev/null | grep -vc -- '-cur.log' || true) reports" ;;
summary)
  { echo "| Run | Bug reports | Last progress line |"; echo "|---|---|---|"
    for d in "$OUT"/*/; do
      n=$(find "$d/logs" -name '*.log' 2>/dev/null | grep -vc -- '-cur.log' || true)
      last=$(grep -E "Executed|queries" "$d/stdout.txt" 2>/dev/null | tail -1 | cut -c1-120)
      echo "| $(basename "$d") | $n | ${last:-} |"
    done; } | tee "$OUT/summary.md" ;;
*) sed -n 2,14p "$0"; exit 2 ;;
esac
