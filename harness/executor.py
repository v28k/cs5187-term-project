"""Run one SQL query through psql and log the result (Stage 1 manual harness).

    python harness/executor.py "SELECT 42"

Configuration comes from the environment, so the script runs on any machine:

    PGFUZZ_PSQL   path to psql            (default: psql on PATH)
    PGHOST/PGPORT/PGUSER/PGDATABASE       standard libpq variables (default 127.0.0.1:5432 postgres/postgres)
    PGFUZZ_LOG    JSONL log file           (default: harness/logs/executions.jsonl)
    PGFUZZ_TIMEOUT seconds per query       (default: 5)

The fuzzing campaigns use pgfuzz.reference.pg_executor.PostgresExecutor instead,
which keeps one connection, isolates test cases and reads the server log.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PSQL = os.environ.get("PGFUZZ_PSQL") or shutil.which("psql") or "psql"
LOG = Path(os.environ.get("PGFUZZ_LOG", HERE / "logs" / "executions.jsonl"))
TIMEOUT = float(os.environ.get("PGFUZZ_TIMEOUT", "5"))


def log_execution(query, status, returncode, output, error):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "status": status,
        "return_code": returncode,
        "stdout": output,
        "stderr": error,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


def execute_query(query):
    env = dict(os.environ)
    env.setdefault("PGHOST", "127.0.0.1")
    env.setdefault("PGPORT", "5432")
    env.setdefault("PGUSER", "postgres")
    env.setdefault("PGDATABASE", "postgres")
    try:
        result = subprocess.run(
            [PSQL, "-X", "-v", "ON_ERROR_STOP=1", "-c", query],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT", None, "", f"Query exceeded {TIMEOUT:g} second timeout"

    if result.returncode == 0:
        status = "SUCCESS"
    elif result.returncode < 0 or result.returncode == 2 or "server closed the connection" in result.stderr:
        # psql exits with 2 when the connection to the server is lost.
        status = "CRASH"
    else:
        status = "ERROR"
    return status, result.returncode, result.stdout, result.stderr


if __name__ == "__main__":
    query = sys.argv[1]

    status, returncode, output, error = execute_query(query)

    log_execution(query, status, returncode, output, error)

    print("Status:", status)
    print("Return code:", returncode)
    print("Output:")
    print(output)
    print("Error:")
    print(error)
