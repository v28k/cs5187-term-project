#!/bin/bash

PG_BIN="$HOME/a3-pg-fuzzing/pg-install/bin"
PG_DATA="$HOME/a3-pg-fuzzing/pg-data"
LOG_FILE="$PG_DATA/server.log"

case "$1" in
    start)
        "$PG_BIN/pg_ctl" \
            -D "$PG_DATA" \
            -l "$LOG_FILE" \
            start
        ;;

    stop)
        "$PG_BIN/pg_ctl" \
            -D "$PG_DATA" \
            stop
        ;;

    status)
        "$PG_BIN/pg_ctl" \
            -D "$PG_DATA" \
            status
        ;;

    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
