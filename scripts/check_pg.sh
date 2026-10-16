#!/bin/bash

PG_BIN="$HOME/a3-pg-fuzzing/pg-install/bin"

echo "PostgreSQL installation:"
"$PG_BIN/postgres" --version
"$PG_BIN/psql" --version
