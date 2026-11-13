"""Line coverage per source file of the SQLite amalgamation from ``sqlite3.c.gcov``.

The amalgamation marks each original file with ``/****** Begin file where.c ******/``; lines
are attributed to the file whose block they are in. ``--table a.json b.json`` renders arms
side by side (markdown), optimizer files first.
"""
import json
import re
import sys
from pathlib import Path

OPT = ("where.c", "wherecode.c", "whereexpr.c", "select.c", "expr.c", "resolve.c", "window.c", "insert.c",
       "update.c", "delete.c", "upsert.c", "analyze.c")
BEGIN = re.compile(r"/\*+ (?:Begin file|Continuing where we left off in) (\S+) \*+/")


def summarize(path):
    cur, cov = "(prologue)", {}
    for line in open(path, encoding="utf-8", errors="replace"):
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        m = BEGIN.search(parts[2])
        if m:
            cur = m.group(1)
            continue
        cnt = parts[0].strip()
        if cnt == "-":
            continue
        c = cov.setdefault(cur, [0, 0])
        c[1] += 1
        c[0] += cnt not in ("#####", "=====")
    total = [sum(v[0] for v in cov.values()), sum(v[1] for v in cov.values())]
    opt = [sum(cov.get(f, [0, 0])[0] for f in OPT), sum(cov.get(f, [0, 0])[1] for f in OPT)]
    return {"files": {k: {"covered": v[0], "lines": v[1]} for k, v in sorted(cov.items())},
            "total": {"covered": total[0], "lines": total[1]}, "optimizer": {"covered": opt[0], "lines": opt[1]}}


def table(paths):
    arms = {Path(p).parent.name: json.loads(Path(p).read_text()) for p in paths}
    rows = ["| File | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    pct = lambda d: f"{100 * d['covered'] / d['lines']:.1f} %" if d and d["lines"] else "-"  # noqa: E731
    rows.append("| **all** | " + " | ".join(pct(a["total"]) for a in arms.values()) + " |")
    rows.append("| **optimizer files** | " + " | ".join(pct(a["optimizer"]) for a in arms.values()) + " |")
    for f in OPT:
        rows.append(f"| {f} | " + " | ".join(pct(a["files"].get(f)) for a in arms.values()) + " |")
    return "\n".join(rows)


if __name__ == "__main__":
    if sys.argv[1] == "--table":
        print(table(sys.argv[2:]))
    else:
        print(json.dumps(summarize(sys.argv[1]), indent=1))
