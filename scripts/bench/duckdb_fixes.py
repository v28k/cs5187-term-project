"""E3: candidate bugs for the DuckDB re-injection benchmark, mined from DuckDB's git history.

A candidate is a non-merge commit that (a) changes C++ under src/ (optimizer, planner, binder,
execution, function), (b) adds or changes a sqllogictest file under test/sql/, (c) says it fixes
something (message mentions fix / issue #), and (d) changes at most --max-files source files
(small fixes revert cleanly and correspond to one bug). Only file names are read, so this also
works on a blob-less partial clone; line counts are checked when the revert is built.

    python scripts/bench/duckdb_fixes.py <duckdb-src> --since 2026-06-01 --out src/bench/duckdb/candidates.json

Then scripts/bench/duckdb_reinject.sh reverts the selected ones on a base commit, builds, and
checks that every fix's own test now fails (the bug is really back) before a campaign runs.
"""
import argparse
import json
import re
import subprocess

AREAS = ("src/optimizer/", "src/planner/", "src/execution/", "src/function/", "src/common/", "src/main/")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def mine(repo, since, until="HEAD", max_files=3, limit=500):
    out = []
    log = git(repo, "log", "--no-merges", f"--since={since}", "--format=@@%H%x09%s", "--name-only", until,
              "--", "src", "test/sql")
    for block in log.split("@@")[1:]:
        lines = block.strip("\n").splitlines()
        sha, subj = lines[0].split("\t", 1)
        if not re.search(r"\bfix|#\d{3,}", subj, re.I):
            continue
        src_files, tests, areas = 0, [], set()
        for path in lines[1:]:
            path = path.strip()
            if path.startswith("src/") and path.endswith((".cpp", ".hpp")):
                src_files += 1
                areas |= {a.split("/")[1] for a in AREAS if path.startswith(a)}
            elif path.startswith("test/sql/") and path.endswith((".test", ".test_slow")):
                tests.append(path)
        if 0 < src_files <= max_files and tests and areas:
            out.append({"sha": sha[:12], "subject": subj, "src_files": src_files, "areas": sorted(areas),
                        "tests": tests, "issues": re.findall(r"#(\d{3,})", subj)})
            if len(out) >= limit:
                break
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", default="HEAD")
    ap.add_argument("--max-files", type=int, default=3)
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--out")
    a = ap.parse_args()
    found = mine(a.repo, a.since, a.until, a.max_files, a.limit)
    text = json.dumps(found, indent=1)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
    by_area = {}
    for f in found:
        for ar in f["areas"]:
            by_area[ar] = by_area.get(ar, 0) + 1
    print(f"{len(found)} candidate fix commits; by area: {by_area}")
