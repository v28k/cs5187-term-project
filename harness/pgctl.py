#!/usr/bin/env python3
"""Manage the Docker fuzzing servers from the host.

    python harness/pgctl.py build [--ref master] [--coverage] [--no-cassert] [--sanitizer asan] [--tag T]
    python harness/pgctl.py up --workers 4 [--image pgfuzz:master] [--base-port 5432]
    python harness/pgctl.py down
    python harness/pgctl.py status
    python harness/pgctl.py coverage --worker 0 [--reset]   # JSON line, used as coverage_command
    python harness/pgctl.py backtrace --worker 0 REPRO.sql  # gdb backtrace of a crash
    python harness/pgctl.py psql --worker 0 -c "SELECT version()"
    python harness/pgctl.py info --worker 0                 # server version, commit, configure flags

Worker i runs in container ``pgfuzz-<i>`` on host port ``base-port + i`` and writes
its server log to ``harness/run/pg-<i>/postgresql.log`` (bind-mounted at /logs).
Point the experiment config at it:

    dsn: "host=localhost port={port} dbname=postgres user=postgres"
    server_log: "{config_dir}/../../harness/run/pg-{worker}/postgresql.log"
    coverage_command: "python {config_dir}/../../harness/pgctl.py coverage --worker {worker}"
    coverage_reset_command: "python {config_dir}/../../harness/pgctl.py coverage --worker {worker} --reset"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / "run"
PREFIX = "pgfuzz-"
SRC_IN_CONTAINER = "/opt/postgres"


def sh(args: list[str], check: bool = True, capture: bool = False, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=check, text=True, capture_output=capture, **kw)


def containers() -> list[str]:
    out = sh(["docker", "ps", "-a", "--filter", f"name={PREFIX}", "--format", "{{.Names}}"], capture=True).stdout
    return sorted(n for n in out.split() if n.startswith(PREFIX))


def cmd_build(a: argparse.Namespace) -> int:
    tag = a.tag or f"pgfuzz:{a.ref}" + ("-cov" if a.coverage else "") + (f"-{a.sanitizer}" if a.sanitizer != "none" else "")
    args = ["docker", "build", "-t", tag, "--build-arg", f"PG_REF={a.ref}",
            "--build-arg", f"CASSERT={0 if a.no_cassert else 1}",
            "--build-arg", f"COVERAGE={1 if a.coverage else 0}",
            "--build-arg", f"SANITIZER={a.sanitizer}", str(HERE / "docker")]
    print(" ".join(args))
    sh(args)
    print(f"built {tag}")
    return 0


def cmd_up(a: argparse.Namespace) -> int:
    for i in range(a.workers):
        name = f"{PREFIX}{i}"
        logdir = RUN / f"pg-{i}"
        logdir.mkdir(parents=True, exist_ok=True)
        sh(["docker", "rm", "-f", name], check=False, capture=True)
        sh(["docker", "run", "-d", "--name", name, "-p", f"{a.base_port + i}:5432",
            "-v", f"{logdir}:/logs", "--shm-size", "1g", "--cap-add", "SYS_PTRACE",
            "--security-opt", "seccomp=unconfined", a.image], capture=True)
        print(f"{name}: port {a.base_port + i}, log {logdir / 'postgresql.log'}")
    for i in range(a.workers):
        _wait_ready(i)
    return 0


def _wait_ready(i: int, timeout: float = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = sh(["docker", "exec", f"{PREFIX}{i}", "pg_isready", "-q"], check=False, capture=True)
        if r.returncode == 0:
            print(f"{PREFIX}{i}: ready")
            return
        time.sleep(1)
    raise SystemExit(f"{PREFIX}{i} did not become ready; see harness/run/pg-{i}/postgresql.log")


def cmd_down(a: argparse.Namespace) -> int:
    for n in containers():
        sh(["docker", "rm", "-f", n], check=False, capture=True)
        print(f"removed {n}")
    return 0


def cmd_status(a: argparse.Namespace) -> int:
    sh(["docker", "ps", "-a", "--filter", f"name={PREFIX}", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"])
    return 0


def cmd_coverage(a: argparse.Namespace) -> int:
    args = ["docker", "exec", f"{PREFIX}{a.worker}", "/opt/fuzz/coverage.sh", SRC_IN_CONTAINER]
    if a.reset:
        args.append("reset")
    r = sh(args, check=False, capture=True)
    lines = [ln for ln in r.stdout.splitlines() if ln.strip().startswith("{")]
    if r.returncode != 0 or not lines:
        print(r.stderr.strip()[-500:], file=sys.stderr)
        return 1
    print(lines[-1])
    return 0


def cmd_backtrace(a: argparse.Namespace) -> int:
    name = f"{PREFIX}{a.worker}"
    sh(["docker", "cp", a.file, f"{name}:/tmp/repro.sql"])
    r = sh(["docker", "exec", name, "/opt/fuzz/gdb_backtrace.sh", "/var/lib/postgresql/data", "/tmp/repro.sql"],
           check=False, capture=True)
    print(r.stdout or r.stderr)
    return r.returncode


def cmd_psql(a: argparse.Namespace) -> int:
    return sh(["docker", "exec", "-i", f"{PREFIX}{a.worker}", "psql", "-U", "postgres", "-X", *a.args], check=False).returncode


def cmd_info(a: argparse.Namespace) -> int:
    name = f"{PREFIX}{a.worker}"
    info = {}
    for key, args in (("version", ["psql", "-U", "postgres", "-XAtc", "SELECT version()"]),
                      ("source_commit", ["cat", "/opt/SOURCE_COMMIT"]),
                      ("configure", ["cat", "/opt/CONFIGURE_FLAGS"])):
        r = sh(["docker", "exec", name, *args], check=False, capture=True)
        info[key] = r.stdout.strip()
    print(json.dumps(info, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("--ref", default="master")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--no-cassert", action="store_true")
    p.add_argument("--sanitizer", default="none", choices=["none", "asan", "ubsan"])
    p.add_argument("--tag")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("up")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--image", default="pgfuzz:master")
    p.add_argument("--base-port", type=int, default=5432)
    p.set_defaults(fn=cmd_up)
    sub.add_parser("down").set_defaults(fn=cmd_down)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("coverage")
    p.add_argument("--worker", type=int, default=0)
    p.add_argument("--reset", action="store_true")
    p.set_defaults(fn=cmd_coverage)
    p = sub.add_parser("backtrace")
    p.add_argument("--worker", type=int, default=0)
    p.add_argument("file")
    p.set_defaults(fn=cmd_backtrace)
    p = sub.add_parser("psql")
    p.add_argument("--worker", type=int, default=0)
    p.add_argument("args", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_psql)
    p = sub.add_parser("info")
    p.add_argument("--worker", type=int, default=0)
    p.set_defaults(fn=cmd_info)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
