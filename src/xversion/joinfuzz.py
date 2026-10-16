"""Cross-version differential fuzzer for join planning.

Generates random queries built from nested INNER/LEFT/RIGHT/FULL joins, pulled-up
and fenced subqueries, LATERAL, sublinks and IS [NOT] NULL tests (including
whole-row tests), and runs each one on two servers: the assert-enabled master
build and a release build (the reference). A different result multiset, or an
error/crash on only one side, is written to the output directory as a
replayable .sql file.

The point is to stress planner code that is new in master (outer-join to
anti-join reduction, join removal on the jointree, self-join elimination,
eager aggregation, ...), where the reference release cannot share the bug.

    python -m xversion.joinfuzz --test-port 5434 --ref-port 5435 -n 20000 --seed 1
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field

import psycopg

# ---------------------------------------------------------------------------
# Schema. Every table has an integer key k (for joins) and a mix of nullable and
# NOT NULL columns. Values are tiny so joins match often.

SCHEMA = r"""
DROP SCHEMA IF EXISTS jf CASCADE;
CREATE SCHEMA jf;
SET search_path = jf;
CREATE TABLE r0 (k int, a int, b int NOT NULL, c text);
CREATE TABLE r1 (k int PRIMARY KEY, a int NOT NULL, b int, c text NOT NULL);
CREATE TABLE r2 (k int NOT NULL, a int, b int, c text, UNIQUE (k));
CREATE TABLE r3 (k int, a int, b int, c text, FOREIGN KEY (k) REFERENCES r1 (k));
CREATE TABLE r4 (k int, a int NOT NULL, b int, c text);
CREATE TABLE r5 (k int NOT NULL, a int, b int GENERATED ALWAYS AS (a * 2) VIRTUAL, c text GENERATED ALWAYS AS ('x' || a) STORED);
CREATE TABLE rp (k int NOT NULL, a int, b int NOT NULL, c text) PARTITION BY RANGE (k);
CREATE TABLE rp0 PARTITION OF rp FOR VALUES FROM (MINVALUE) TO (3);
CREATE TABLE rp1 PARTITION OF rp FOR VALUES FROM (3) TO (MAXVALUE);
CREATE TABLE ri (k int, a int, b int, c text);
CREATE TABLE ri_c (b int NOT NULL) INHERITS (ri);
"""

DATA = r"""
SET search_path = jf;
INSERT INTO r1 SELECT g, g % 3, NULLIF(g % 4, 0), 't' || (g % 2) FROM generate_series(0, 6) g;
INSERT INTO r0 SELECT NULLIF(g % 6, 5), NULLIF(g % 3, 1), g % 4, CASE WHEN g % 5 = 0 THEN NULL ELSE 't' || (g % 3) END FROM generate_series(0, 9) g;
INSERT INTO r2 SELECT g, NULLIF(g % 2, 0), g % 3, NULL FROM generate_series(1, 5) g;
INSERT INTO r3 SELECT NULLIF(g % 7, 6), g % 3, NULLIF(g % 2, 1), 't' || g FROM generate_series(0, 8) g;
INSERT INTO r4 SELECT g % 5, g % 2, CASE WHEN g = 3 THEN NULL ELSE g END, NULL FROM generate_series(0, 6) g;
-- r4.b holds a NULL that the NOT VALID constraint does not vouch for
ALTER TABLE r4 ADD CONSTRAINT r4_b_nn NOT NULL b NOT VALID;
INSERT INTO r5 (k, a) SELECT g, NULLIF(g % 3, 2) FROM generate_series(0, 5) g;
INSERT INTO rp SELECT g, NULLIF(g % 2, 1), g % 3, 't' || g FROM generate_series(0, 6) g;
INSERT INTO ri SELECT g, g % 2, NULLIF(g, 2), NULL FROM generate_series(0, 3) g;
INSERT INTO ri_c SELECT g, NULL, g, 'c' FROM generate_series(2, 5) g;
ANALYZE;
"""

TABLES = {
    "r0": ["k", "a", "b", "c"],
    "r1": ["k", "a", "b", "c"],
    "r2": ["k", "a", "b", "c"],
    "r3": ["k", "a", "b", "c"],
    "r4": ["k", "a", "b", "c"],
    "r5": ["k", "a", "b", "c"],
    "rp": ["k", "a", "b", "c"],
    "ri": ["k", "a", "b", "c"],
}
INT_COLS = ["k", "a", "b"]


@dataclass
class Rel:
    """A FROM item: its SQL text and the aliases (with their columns) it exposes."""
    sql: str
    aliases: list[str] = field(default_factory=list)


class Gen:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.n = 0

    def alias(self) -> str:
        self.n += 1
        return f"x{self.n}"

    # -- expressions --------------------------------------------------------
    def col(self, aliases: list[str], cols=INT_COLS) -> str:
        return f"{self.rng.choice(aliases)}.{self.rng.choice(cols)}"

    def lit(self) -> str:
        return self.rng.choice(["0", "1", "2", "3", "NULL::int"])

    def scalar(self, aliases: list[str]) -> str:
        r = self.rng.random()
        if r < 0.65:
            return self.col(aliases)
        if r < 0.75:
            return self.lit()
        if r < 0.85:
            return f"coalesce({self.col(aliases)}, {self.lit()})"
        if r < 0.92:
            return f"({self.col(aliases)} + {self.rng.choice(['0', '1'])})"
        return f"nullif({self.col(aliases)}, {self.lit()})"

    def pred(self, aliases: list[str], depth: int = 0, outer: list[str] | None = None) -> str:
        r = self.rng.random()
        if depth < 2 and r < 0.12:
            return f"({self.pred(aliases, depth + 1, outer)} {self.rng.choice(['AND', 'OR'])} {self.pred(aliases, depth + 1, outer)})"
        if depth < 2 and r < 0.16:
            return f"NOT ({self.pred(aliases, depth + 1, outer)})"
        if r < 0.36:
            return f"{self.col(aliases)} IS NULL"
        if r < 0.46:
            return f"{self.col(aliases)} IS NOT NULL"
        if r < 0.54:
            return f"{self.rng.choice(aliases)} IS {self.rng.choice(['NULL', 'NOT NULL'])}"  # whole-row
        if r < 0.60:
            return f"({self.col(aliases)} = {self.col(aliases)}) IS {self.rng.choice(['UNKNOWN', 'NOT TRUE', 'FALSE'])}"
        if r < 0.70 and depth < 2:
            return self.sublink(aliases, outer)
        if r < 0.74:
            return f"{self.col(aliases)} IS DISTINCT FROM {self.scalar(aliases)}"
        if r < 0.78:
            return f"{self.col(aliases)} IN ({self.lit()}, {self.lit()})"
        op = self.rng.choice(["=", "<", ">", "<>", "<=", ">="])
        return f"{self.scalar(aliases)} {op} {self.scalar(aliases)}"

    def sublink(self, aliases: list[str], outer: list[str] | None) -> str:
        t = self.rng.choice(list(TABLES))
        a = self.alias()
        corr = f"{a}.{self.rng.choice(INT_COLS)} = {self.col(aliases)}"
        inner_pred = corr if self.rng.random() < 0.8 else self.pred([a], 2)
        if self.rng.random() < 0.3:
            inner_pred += f" AND {self.pred([a], 2)}"
        kind = self.rng.random()
        if kind < 0.35:
            return f"EXISTS (SELECT 1 FROM {t} {a} WHERE {inner_pred})"
        if kind < 0.6:
            return f"NOT EXISTS (SELECT 1 FROM {t} {a} WHERE {inner_pred})"
        c = self.rng.choice(INT_COLS)
        nn = f" WHERE {a}.{c} IS NOT NULL" if self.rng.random() < 0.5 else ""
        if kind < 0.8:
            return f"{self.col(aliases)} NOT IN (SELECT {a}.{c} FROM {t} {a}{nn})"
        return f"{self.col(aliases)} IN (SELECT {a}.{c} FROM {t} {a}{nn})"

    # -- FROM items -----------------------------------------------------------
    def base(self, outer: list[str]) -> Rel:
        a = self.alias()
        r = self.rng.random()
        t = self.rng.choice(list(TABLES))
        if r < 0.62:
            return Rel(f"{t} {a}", [a])
        cols = ", ".join(TABLES[t])
        if r < 0.80:
            # pulled-up subquery, possibly with a strict qual that can serve as a proof
            w = f" WHERE {self.pred(['s'], 1)}" if self.rng.random() < 0.6 else ""
            return Rel(f"(SELECT {cols} FROM {t} s{w}) {a}", [a])
        if r < 0.88:
            # fenced subquery (not pulled up)
            w = f" WHERE {self.pred(['s'], 1)}" if self.rng.random() < 0.5 else ""
            return Rel(f"(SELECT {cols} FROM {t} s{w} OFFSET 0) {a}", [a])
        if r < 0.94 and outer:
            # LATERAL subquery referencing an earlier FROM item
            w = f"s.{self.rng.choice(INT_COLS)} = {self.col(outer)}"
            if self.rng.random() < 0.4:
                w += f" AND {self.pred(['s'], 1)}"
            return Rel(f"LATERAL (SELECT {cols} FROM {t} s WHERE {w}) {a}", [a])
        # grouped / distinct subquery
        if self.rng.random() < 0.5:
            return Rel(f"(SELECT DISTINCT k, a, b, c FROM {t} s) {a}", [a])
        return Rel(f"(SELECT s.k, max(s.a) AS a, count(s.b)::int AS b, min(s.c) AS c FROM {t} s GROUP BY s.k) {a}", [a])

    def from_tree(self, depth: int, outer: list[str]) -> Rel:
        if depth <= 0 or self.rng.random() < 0.3:
            return self.base(outer)
        left = self.from_tree(depth - 1, outer)
        right = self.from_tree(depth - 1, outer + left.aliases)
        if right.sql.startswith("LATERAL"):
            jt = self.rng.choice(["JOIN", "LEFT JOIN", "LEFT JOIN", "CROSS JOIN"])
        else:
            jt = self.rng.choice(["JOIN", "LEFT JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "FULL JOIN", "CROSS JOIN"])
        both = left.aliases + right.aliases
        if jt == "CROSS JOIN":
            return Rel(f"({left.sql} {jt} {right.sql})", both)
        conds = [f"{self.col(left.aliases)} = {self.col(right.aliases)}"]
        if jt == "FULL JOIN":
            # FULL JOIN needs a merge- or hash-joinable condition
            if self.rng.random() < 0.3:
                conds.append(f"{self.col(left.aliases)} = {self.col(right.aliases)}")
        else:
            while self.rng.random() < 0.35:
                conds.append(self.pred(both, 1))
        return Rel(f"({left.sql} {jt} {right.sql} ON {' AND '.join(conds)})", both)

    def query(self) -> str:
        fr = self.from_tree(self.rng.choice([1, 2, 2, 3, 3, 4]), [])
        aliases = fr.aliases
        nwhere = self.rng.choice([0, 1, 1, 2, 3])
        where = " AND ".join(self.pred(aliases) for _ in range(nwhere))
        where = f" WHERE {where}" if where else ""
        r = self.rng.random()
        if r < 0.15:
            g = self.col(aliases)
            return f"SELECT {g}, count(*), count({self.col(aliases)}), sum({self.col(aliases)}) FROM {fr.sql}{where} GROUP BY {g}"
        if r < 0.22:
            return f"SELECT count(*), count({self.col(aliases)}), min({self.col(aliases)}) FROM {fr.sql}{where}"
        cols = ", ".join(f"{a}.*" if self.rng.random() < 0.3 else self.col([a], ["k", "a", "b", "c"]) for a in aliases)
        distinct = "DISTINCT " if self.rng.random() < 0.15 else ""
        return f"SELECT {distinct}{cols} FROM {fr.sql}{where}"


# ---------------------------------------------------------------------------

def connect(port: int):
    conn = psycopg.connect(f"host=127.0.0.1 port={port} dbname=postgres user=postgres", autocommit=True)
    return conn


def setup(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute(DATA)


def run(conn, sql: str, timeout_ms: int):
    """Returns ('ok', sorted rows) or ('error', sqlstate, message) or ('crash', message)."""
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = {timeout_ms}")
            cur.execute("SET search_path = jf")
            cur.execute(sql)
            rows = cur.fetchall()
            return ("ok", sorted(repr(r) for r in rows))
    except psycopg.errors.QueryCanceled:
        return ("timeout",)
    except psycopg.OperationalError as e:
        return ("crash", str(e).strip())
    except psycopg.Error as e:
        return ("error", e.sqlstate, str(e).strip().splitlines()[0])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test-port", type=int, default=5434)
    ap.add_argument("--ref-port", type=int, default=5435)
    ap.add_argument("-n", type=int, default=1000, help="number of queries")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--timeout-ms", type=int, default=3000)
    ap.add_argument("--out", default="results/joinfuzz")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(args.seed)
    test, ref = connect(args.test_port), connect(args.ref_port)
    setup(test)
    setup(ref)
    stats = {"queries": 0, "ok": 0, "both_error": 0, "mismatch": 0, "crash": 0, "one_side_error": 0, "timeout": 0}
    t0 = time.time()
    for i in range(args.n):
        sql = Gen(rng).query()
        rt = run(test, sql, args.timeout_ms)
        if rt[0] == "crash":
            stats["crash"] += 1
            save(args.out, "crash", i, args.seed, sql, rt, None)
            time.sleep(5)  # crash recovery
            test = reconnect(args.test_port)
            continue
        if rt[0] == "timeout":
            stats["timeout"] += 1
            continue
        rr = run(ref, sql, args.timeout_ms)
        stats["queries"] += 1
        if rr[0] == "crash":
            ref = reconnect(args.ref_port)
            continue
        if rt[0] == "ok" and rr[0] == "ok":
            if rt[1] != rr[1]:
                stats["mismatch"] += 1
                save(args.out, "mismatch", i, args.seed, sql, rt, rr)
            else:
                stats["ok"] += 1
        elif rt[0] == "error" and rr[0] == "error":
            stats["both_error"] += 1
        elif rr[0] != "timeout":
            stats["one_side_error"] += 1
            save(args.out, "oneside", i, args.seed, sql, rt, rr)
        if (i + 1) % 1000 == 0:
            print(json.dumps({"i": i + 1, "s": round(time.time() - t0, 1), **stats}), flush=True)
    print(json.dumps({"done": True, "s": round(time.time() - t0, 1), **stats}), flush=True)
    return 0


def reconnect(port: int):
    for _ in range(60):
        try:
            return connect(port)
        except psycopg.OperationalError:
            time.sleep(1)
    raise SystemExit(f"server on port {port} did not come back")


def save(out: str, kind: str, i: int, seed: int, sql: str, rt, rr) -> None:
    path = os.path.join(out, f"{kind}-s{seed}-{i}.sql")
    with open(path, "w") as f:
        f.write(f"-- joinfuzz {kind}, seed {seed}, query {i}\n")
        f.write(f"-- test: {str(rt)[:2000]}\n-- ref:  {str(rr)[:2000]}\n")
        f.write("SET search_path = jf;\n")
        f.write(sql + ";\n")


if __name__ == "__main__":
    sys.exit(main())
