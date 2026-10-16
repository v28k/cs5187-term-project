#!/usr/bin/env bash
# Initialise the cluster on first start, then run the postmaster in the foreground
# with stderr (including TRAP: lines and backtraces) appended to /logs/postgresql.log.
set -euo pipefail

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  initdb -D "$PGDATA" -U postgres --auth=trust --no-instructions >/dev/null
  cat /opt/fuzz/postgresql.fuzz.conf >> "$PGDATA/postgresql.conf"
  if postgres --describe-config 2>/dev/null | grep -q '^backtrace_on_internal_error'; then
    echo "backtrace_on_internal_error = on" >> "$PGDATA/postgresql.conf"
  fi
  echo "host all all 0.0.0.0/0 trust" >> "$PGDATA/pg_hba.conf"
  echo "host all all ::/0 trust" >> "$PGDATA/pg_hba.conf"
fi

touch /logs/postgresql.log
chmod 755 /logs || true
chmod 644 /logs/postgresql.log || true
cp /opt/SOURCE_COMMIT /opt/CONFIGURE_FLAGS /logs/ 2>/dev/null || true

if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec postgres -D "$PGDATA" >>/logs/postgresql.log 2>&1
