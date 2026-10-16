"""Cross-version differential fuzzer for join and aggregate planning, v2.

Like joinfuzz, every query runs on the assert-enabled master build (test) and on
a release build (reference), and a different result multiset, or an error or
crash on one side only, is saved as a replayable .sql file. Differences from v1:

* larger tables (tens to a few hundred rows) with int2/int4/int8/numeric/text
  columns, so that eager aggregation, memoize, partitionwise and parallel plans
  are actually chosen, and cross-type join keys occur;
* each master query runs under a random set of planner settings (eager
  aggregation forced, join methods disabled, partitionwise on, parallel forced,
  ...), recorded in the saved file; the reference runs the plain query;
* more shapes: GROUP BY aggregates over joins (with FILTER), USING joins,
  self-joins on unique keys, UNION ALL appendrels, grouping sets, window
  functions, scalar sublinks.

    python -m xversion.joinfuzz2 --test-port 5434 --ref-port 5435 -n 20000 --seed 1
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

SCHEMA = r"""
DROP SCHEMA IF EXISTS jf2 CASCADE;
CREATE SCHEMA jf2;
SET search_path = jf2;
CREATE TABLE u1 (k int PRIMARY KEY, a int NOT NULL, b int, s int2, n numeric, t text NOT NULL);
CREATE TABLE u2 (k int NOT NULL UNIQUE, a int, b int8, s int2 NOT NULL, n numeric, t text);
CREATE TABLE f1 (k int REFERENCES u1, a int, b int8, s int2, n numeric, t text);
CREATE TABLE f2 (k int, a int NOT NULL, b int, s int2, n numeric NOT NULL, t text);
CREATE TABLE g1 (k int NOT NULL, a int, b int GENERATED ALWAYS AS (a + 1) VIRTUAL, s int2, n numeric, t text);
CREATE TABLE p1 (k int NOT NULL, a int, b int NOT NULL, s int2, n numeric, t text) PARTITION BY HASH (k);
CREATE TABLE p1_0 PARTITION OF p1 FOR VALUES WITH (MODULUS 3, REMAINDER 0);
CREATE TABLE p1_1 PARTITION OF p1 FOR VALUES WITH (MODULUS 3, REMAINDER 1);
CREATE TABLE p1_2 PARTITION OF p1 FOR VALUES WITH (MODULUS 3, REMAINDER 2);
CREATE TABLE p2 (k int NOT NULL, a int, b int, s int2, n numeric, t text) PARTITION BY HASH (k);
CREATE TABLE p2_0 PARTITION OF p2 FOR VALUES WITH (MODULUS 3, REMAINDER 0);
CREATE TABLE p2_1 PARTITION OF p2 FOR VALUES WITH (MODULUS 3, REMAINDER 1);
CREATE TABLE p2_2 PARTITION OF p2 FOR VALUES WITH (MODULUS 3, REMAINDER 2);
CREATE TABLE h1 (k int, a int, b int, s int2, n numeric, t text);
CREATE TABLE h1_c (a int NOT NULL) INHERITS (h1);
"""

DATA = r"""
SET search_path = jf2;
INSERT INTO u1 SELECT g, g % 7, NULLIF(g % 5, 0), (g % 4)::int2, (g % 3) / 2.0, 't' || (g % 6) FROM generate_series(0, 49) g;
INSERT INTO u2 SELECT g, NULLIF(g % 6, 3), g % 9, (g % 5)::int2, CASE WHEN g % 4 = 0 THEN NULL ELSE g % 3 END, CASE WHEN g % 7 = 0 THEN NULL ELSE 't' || (g % 4) END FROM generate_series(10, 69) g;
INSERT INTO f1 SELECT NULLIF(g % 53, 52) % 50, g % 11, NULLIF(g % 8, 7), (g % 3)::int2, g % 5, 't' || (g % 3) FROM generate_series(0, 299) g;
INSERT INTO f2 SELECT g % 40, g % 6, NULLIF(g % 10, 4), NULLIF(g % 6, 1)::int2, (g % 4) * 1.0, CASE WHEN g % 9 = 0 THEN NULL ELSE 't' || (g % 5) END FROM generate_series(0, 199) g;
INSERT INTO g1 (k, a, s, n, t) SELECT g, NULLIF(g % 5, 2), (g % 3)::int2, g % 2, 't' || (g % 2) FROM generate_series(0, 59) g;
INSERT INTO p1 SELECT g, NULLIF(g % 4, 1), g % 7, (g % 5)::int2, g % 3, 't' || (g % 3) FROM generate_series(0, 89) g;
INSERT INTO p2 SELECT g % 45, g % 8, NULLIF(g % 6, 0), (g % 2)::int2, g % 4, 't' || (g % 2) FROM generate_series(0, 134) g;
INSERT INTO h1 SELECT g, NULLIF(g % 3, 0), g % 5, (g % 4)::int2, g % 2, 't' || (g % 3) FROM generate_series(0, 29) g;
INSERT INTO h1_c SELECT g, g % 4, NULLIF(g % 3, 1), (g % 2)::int2, g % 3, NULL FROM generate_series(20, 49) g;
CREATE INDEX ON f1 (k);
CREATE INDEX ON f1 (a, b);
CREATE INDEX ON f2 (k, a);
CREATE INDEX ON p1 (a);
CREATE INDEX ON p2 (k);
CREATE INDEX ON g1 (k);
ANALYZE;
"""

TABLES = ["u1", "u2", "f1", "f2", "g1", "p1", "p2", "h1"]
COLS = ["k", "a", "b", "s", "n", "t"]
NUMCOLS = ["k", "a", "b", "s", "n"]
INTCOLS = ["k", "a", "b", "s"]

# Planner settings for the test side. Each query gets a random subset.
GUCS = [
    ("enable_eager_aggregate", ["on", "off"]),
    ("min_eager_agg_group_size", ["0", "1"]),
    ("enable_hashjoin", ["off"]),
    ("enable_mergejoin", ["off"]),
    ("enable_nestloop", ["off"]),
    ("enable_hashagg", ["off"]),
    ("enable_sort", ["off"]),
    ("enable_seqscan", ["off"]),
    ("enable_memoize", ["off"]),
    ("enable_material", ["off"]),
    ("enable_self_join_elimination", ["off"]),
    ("enable_partitionwise_join", ["on"]),
    ("enable_partitionwise_aggregate", ["on"]),
    ("enable_partition_pruning", ["off"]),
    ("enable_group_by_reordering", ["off"]),
    ("enable_incremental_sort", ["off"]),
    ("enable_presorted_aggregate", ["off"]),
    ("enable_groupagg", ["off"]),
    ("join_collapse_limit", ["1"]),
    ("from_collapse_limit", ["1"]),
    ("work_mem", ["64kB"]),
    ("debug_parallel_query", ["on"]),
]
PARALLEL = ["SET LOCAL parallel_setup_cost = 0", "SET LOCAL parallel_tuple_cost = 0",
            "SET LOCAL min_parallel_table_scan_size = 0", "SET LOCAL max_parallel_workers_per_gather = 2"]


@dataclass
class Rel:
    sql: str
    aliases: list[str] = field(default_factory=list)


class Gen:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.n = 0

    def alias(self) -> str:
        self.n += 1
        return f"x{self.n}"

    def col(self, aliases, cols=NUMCOLS) -> str:
        return f"{self.rng.choice(aliases)}.{self.rng.choice(cols)}"

    def lit(self) -> str:
        return self.rng.choice(["0", "1", "2", "3", "5", "NULL::int", "1.0", "2::int2"])

    def scalar(self, aliases) -> str:
        r = self.rng.random()
        if r < 0.6:
            return self.col(aliases)
        if r < 0.7:
            return self.lit()
        if r < 0.78:
            return f"coalesce({self.col(aliases, INTCOLS)}, {self.rng.choice(['0', '1'])})"
        if r < 0.86:
            return f"({self.col(aliases, INTCOLS)} {self.rng.choice(['+', '-', '*', '%'])} {self.rng.choice(['1', '2', '3'])})"
        if r < 0.92:
            return f"nullif({self.col(aliases, INTCOLS)}, {self.rng.choice(['0', '1'])})"
        return f"length({self.col(aliases, ['t'])})"

    def pred(self, aliases, depth=0) -> str:
        r = self.rng.random()
        if depth < 2 and r < 0.12:
            return f"({self.pred(aliases, depth + 1)} {self.rng.choice(['AND', 'OR'])} {self.pred(aliases, depth + 1)})"
        if depth < 2 and r < 0.15:
            return f"NOT ({self.pred(aliases, depth + 1)})"
        if r < 0.30:
            return f"{self.col(aliases, COLS)} IS NULL"
        if r < 0.40:
            return f"{self.col(aliases, COLS)} IS NOT NULL"
        if r < 0.44:
            return f"{self.rng.choice(aliases)} IS {self.rng.choice(['NULL', 'NOT NULL'])}"
        if r < 0.52 and depth < 2:
            return self.sublink(aliases)
        if r < 0.56:
            return f"{self.col(aliases)} IS DISTINCT FROM {self.scalar(aliases)}"
        if r < 0.62:
            return f"{self.col(aliases, INTCOLS)} IN ({self.lit()}, {self.lit()}, {self.lit()})"
        if r < 0.66:
            return f"{self.col(aliases, ['t'])} {self.rng.choice(['=', '<', 'LIKE'])} {self.rng.choice(['''t1''', '''t2''', '''t%'''])}"
        if r < 0.70:
            return f"{self.col(aliases)} BETWEEN {self.lit()} AND {self.lit()}"
        op = self.rng.choice(["=", "=", "<", ">", "<>", "<=", ">="])
        return f"{self.scalar(aliases)} {op} {self.scalar(aliases)}"

    def sublink(self, aliases) -> str:
        t = self.rng.choice(TABLES)
        a = self.alias()
        cond = f"{a}.{self.rng.choice(INTCOLS)} = {self.col(aliases, INTCOLS)}"
        if self.rng.random() < 0.3:
            cond += f" AND {self.pred([a], 2)}"
        k = self.rng.random()
        if k < 0.25:
            return f"EXISTS (SELECT 1 FROM {t} {a} WHERE {cond})"
        if k < 0.45:
            return f"NOT EXISTS (SELECT 1 FROM {t} {a} WHERE {cond})"
        c = self.rng.choice(INTCOLS)
        nn = f" WHERE {a}.{c} IS NOT NULL" if self.rng.random() < 0.5 else ""
        if k < 0.6:
            return f"{self.col(aliases, INTCOLS)} NOT IN (SELECT {a}.{c} FROM {t} {a}{nn})"
        if k < 0.8:
            return f"{self.col(aliases, INTCOLS)} IN (SELECT {a}.{c} FROM {t} {a}{nn})"
        agg = self.rng.choice(["max", "min", "count", "sum"])
        return f"{self.col(aliases, INTCOLS)} {self.rng.choice(['=', '<', '>='])} (SELECT {agg}({a}.{c}) FROM {t} {a} WHERE {cond})"

    def base(self, outer) -> Rel:
        a = self.alias()
        t = self.rng.choice(TABLES)
        cols = ", ".join(COLS)
        r = self.rng.random()
        if r < 0.55:
            return Rel(f"{t} {a}", [a])
        if r < 0.68:
            w = f" WHERE {self.pred(['s'], 1)}" if self.rng.random() < 0.6 else ""
            return Rel(f"(SELECT {cols} FROM {t} s{w}) {a}", [a])
        if r < 0.73:
            # subquery output with non-strict expressions: PlaceHolderVars when nulled
            return Rel(f"(SELECT s.k, coalesce(s.a, -1) AS a, 1 AS b, s.s, s.n, s.t FROM {t} s) {a}", [a])
        if r < 0.78:
            t2 = self.rng.choice(TABLES)
            return Rel(f"(SELECT {cols} FROM {t} s UNION ALL SELECT {cols} FROM {t2} s2) {a}", [a])
        if r < 0.82:
            w = f" WHERE {self.pred(['s'], 1)}" if self.rng.random() < 0.5 else ""
            return Rel(f"(SELECT {cols} FROM {t} s{w} OFFSET 0) {a}", [a])
        if r < 0.90 and outer:
            w = f"s.{self.rng.choice(INTCOLS)} = {self.col(outer, INTCOLS)}"
            if self.rng.random() < 0.4:
                w += f" AND {self.pred(['s'], 1)}"
            if self.rng.random() < 0.3:
                return Rel(f"LATERAL (SELECT s.k, count(*)::int AS a, max(s.b) AS b, min(s.s) AS s, sum(s.n) AS n, min(s.t) AS t FROM {t} s WHERE {w} GROUP BY s.k) {a}", [a])
            return Rel(f"LATERAL (SELECT {cols} FROM {t} s WHERE {w}) {a}", [a])
        if r < 0.95:
            return Rel(f"(SELECT DISTINCT {cols} FROM {t} s) {a}", [a])
        return Rel(f"(SELECT s.k, max(s.a) AS a, count(s.b)::int AS b, min(s.s) AS s, sum(s.n) AS n, max(s.t) AS t FROM {t} s GROUP BY s.k) {a}", [a])

    def join_cond(self, left, right, jt) -> str:
        r = self.rng.random()
        if r < 0.2 and len(left.aliases) == 1 and len(right.aliases) == 1 and jt != "FULL JOIN":
            return "USING"
        if r < 0.55:
            c = self.rng.choice(INTCOLS)
            conds = [f"{self.rng.choice(left.aliases)}.{c} = {self.rng.choice(right.aliases)}.{c}"]
        elif r < 0.65:
            conds = [f"{self.rng.choice(left.aliases)}.t = {self.rng.choice(right.aliases)}.t"]
        else:
            conds = [f"{self.col(left.aliases, INTCOLS)} = {self.col(right.aliases, INTCOLS)}"]
        if jt == "FULL JOIN":
            if self.rng.random() < 0.3:
                conds.append(f"{self.col(left.aliases, INTCOLS)} = {self.col(right.aliases, INTCOLS)}")
        else:
            while self.rng.random() < 0.3:
                conds.append(self.pred(left.aliases + right.aliases, 1))
        return " AND ".join(conds)

    def from_tree(self, depth, outer) -> Rel:
        if depth <= 0 or self.rng.random() < 0.25:
            return self.base(outer)
        if self.rng.random() < 0.12:
            # self-join on a unique key (self-join elimination)
            t = self.rng.choice(["u1", "u2"])
            a, b = self.alias(), self.alias()
            extra = f" AND {self.pred([a, b], 1)}" if self.rng.random() < 0.5 else ""
            return Rel(f"({t} {a} JOIN {t} {b} ON {a}.k = {b}.k{extra})", [a, b])
        left = self.from_tree(depth - 1, outer)
        right = self.from_tree(depth - 1, outer + left.aliases)
        if right.sql.startswith("LATERAL"):
            jt = self.rng.choice(["JOIN", "LEFT JOIN", "LEFT JOIN", "CROSS JOIN"])
        else:
            jt = self.rng.choice(["JOIN", "JOIN", "LEFT JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"])
        both = left.aliases + right.aliases
        if jt == "CROSS JOIN":
            return Rel(f"({left.sql} {jt} {right.sql})", both)
        cond = self.join_cond(left, right, jt)
        if cond == "USING":
            c = self.rng.choice(["k", "a", "t"])
            # USING merges the column; keep referring to the qualified sides
            return Rel(f"({left.sql} {jt} {right.sql} USING ({c}))", both)
        return Rel(f"({left.sql} {jt} {right.sql} ON {cond})", both)

    def agg(self, aliases) -> str:
        f = self.rng.choice(["count(*)", "count({c})", "sum({c})", "min({c})", "max({c})", "avg({c})",
                             "count(DISTINCT {c})", "bool_or({c} > 1)", "sum({c}) FILTER (WHERE {p})",
                             "count(*) FILTER (WHERE {p})", "max({t})"])
        return f.format(c=self.col(aliases, INTCOLS + ["n"]), p=self.pred(aliases, 2), t=self.col(aliases, ["t"]))

    def query(self) -> str:
        fr = self.from_tree(self.rng.choice([1, 2, 2, 3, 3, 4]), [])
        al = fr.aliases
        nwhere = self.rng.choice([0, 1, 1, 2, 3])
        where = " AND ".join(self.pred(al) for _ in range(nwhere))
        where = f" WHERE {where}" if where else ""
        r = self.rng.random()
        if r < 0.40:
            keys = [self.col(al, COLS) for _ in range(self.rng.choice([1, 1, 2, 3]))]
            keys = list(dict.fromkeys(keys))
            aggs = ", ".join(self.agg(al) for _ in range(self.rng.choice([1, 2, 3])))
            gb = ", ".join(keys)
            if self.rng.random() < 0.12:
                gb = self.rng.choice([f"ROLLUP ({gb})", f"CUBE ({gb})", f"GROUPING SETS (({gb}), ())"])
            having = f" HAVING {self.agg(al)} > {self.rng.choice(['0', '1', '2'])}" if self.rng.random() < 0.2 else ""
            return f"SELECT {', '.join(keys)}, {aggs} FROM {fr.sql}{where} GROUP BY {gb}{having}"
        if r < 0.47:
            return f"SELECT {', '.join(self.agg(al) for _ in range(2))} FROM {fr.sql}{where}"
        if r < 0.52:
            c = self.col(al, INTCOLS)
            return f"SELECT {c}, count(*) OVER (PARTITION BY {c}), sum({self.col(al, INTCOLS)}) OVER (PARTITION BY {c}) FROM {fr.sql}{where}"
        cols = ", ".join(f"{a}.*" if self.rng.random() < 0.25 else self.col([a], COLS) for a in al)
        distinct = "DISTINCT " if self.rng.random() < 0.15 else ""
        return f"SELECT {distinct}{cols} FROM {fr.sql}{where}"

    def settings(self) -> list[str]:
        out = []
        for name, vals in self.rng.sample(GUCS, self.rng.choice([0, 1, 2, 3, 4])):
            out.append(f"SET LOCAL {name} = {self.rng.choice(vals)}")
            if name == "debug_parallel_query":
                out.extend(PARALLEL)
        if self.rng.random() < 0.4 and not any("min_eager" in s for s in out):
            out.append("SET LOCAL min_eager_agg_group_size = 0")
        return out


def connect(port: int):
    return psycopg.connect(f"host=127.0.0.1 port={port} dbname=postgres user=postgres", autocommit=True)


def setup(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute(DATA)


def norm(v):
    # numeric results such as avg() may differ in trailing digits between versions only by scale
    if hasattr(v, "normalize") and not isinstance(v, (int, float)):
        try:
            return str(round(v, 10).normalize())
        except Exception:
            return str(v)
    if isinstance(v, float):
        return repr(round(v, 9))
    return repr(v)


def run(conn, sql: str, sets: list[str], timeout_ms: int):
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
                cur.execute("SET LOCAL search_path = jf2")
                for s in sets:
                    cur.execute(s)
                cur.execute(sql)
                rows = cur.fetchall()
                return ("ok", sorted("|".join(norm(v) for v in r) for r in rows))
    except psycopg.errors.QueryCanceled:
        return ("timeout",)
    except psycopg.OperationalError as e:
        return ("crash", str(e).strip())
    except psycopg.Error as e:
        return ("error", e.sqlstate, str(e).strip().splitlines()[0])


def reconnect(port: int):
    for _ in range(90):
        try:
            return connect(port)
        except psycopg.OperationalError:
            time.sleep(1)
    raise SystemExit(f"server on port {port} did not come back")


def save(out, kind, i, seed, sql, sets, rt, rr) -> None:
    path = os.path.join(out, f"{kind}-s{seed}-{i}.sql")
    with open(path, "w") as f:
        f.write(f"-- joinfuzz2 {kind}, seed {seed}, query {i}\n")
        f.write(f"-- test: {str(rt)[:3000]}\n-- ref:  {str(rr)[:3000]}\n")
        f.write("BEGIN;\nSET LOCAL search_path = jf2;\n")
        for s in sets:
            f.write(s + ";\n")
        f.write(sql + ";\nROLLBACK;\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test-port", type=int, default=5434)
    ap.add_argument("--ref-port", type=int, default=5435)
    ap.add_argument("-n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--timeout-ms", type=int, default=5000)
    ap.add_argument("--out", default="results/joinfuzz2")
    ap.add_argument("--no-setup", action="store_true", help="reuse the jf2 schema already on both servers")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(args.seed)
    test, ref = connect(args.test_port), connect(args.ref_port)
    if not args.no_setup:
        setup(test)
        setup(ref)
    st = {"queries": 0, "ok": 0, "both_error": 0, "mismatch": 0, "crash": 0, "one_side_error": 0, "timeout": 0}
    t0 = time.time()
    for i in range(args.n):
        g = Gen(rng)
        sql = g.query()
        sets = g.settings()
        rt = run(test, sql, sets, args.timeout_ms)
        if rt[0] == "crash":
            st["crash"] += 1
            save(args.out, "crash", i, args.seed, sql, sets, rt, None)
            time.sleep(5)
            test = reconnect(args.test_port)
            continue
        if rt[0] == "timeout":
            st["timeout"] += 1
            continue
        rr = run(ref, sql, [], args.timeout_ms)
        st["queries"] += 1
        if rr[0] == "crash":
            ref = reconnect(args.ref_port)
            continue
        if rt[0] == "ok" and rr[0] == "ok":
            if rt[1] != rr[1]:
                st["mismatch"] += 1
                save(args.out, "mismatch", i, args.seed, sql, sets, rt, rr)
            else:
                st["ok"] += 1
        elif rt[0] == "error" and rr[0] == "error":
            st["both_error"] += 1
        elif rr[0] != "timeout":
            st["one_side_error"] += 1
            save(args.out, "oneside", i, args.seed, sql, sets, rt, rr)
        if (i + 1) % 2000 == 0:
            print(json.dumps({"i": i + 1, "s": round(time.time() - t0, 1), **st}), flush=True)
    print(json.dumps({"done": True, "seed": args.seed, "s": round(time.time() - t0, 1), **st}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
