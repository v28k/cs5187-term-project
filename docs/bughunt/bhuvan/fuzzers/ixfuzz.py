"""Differential fuzzer: btree index scans vs sequential scan.

Random table (a,b,c int with NULLs and many duplicates), random multi-column
btree index (column order, ASC/DESC, NULLS FIRST/LAST), random predicates
(row comparisons, = ANY / <> ALL arrays incl. NULL elements, IN, BETWEEN,
redundant and contradictory inequality chains, cross-type int2/int8
constants, IS [NOT] NULL), and ordered queries in both directions.

Modes: SEQ (seqscan only), IDX (index scan forced), IOS (index-only scan
forced, selecting only indexed columns), BMP (bitmap scan forced).
usage: ixfuzz.py PORT SEED N [--verbose]
"""
import json, os, random, sys
import psycopg

DOM = list(range(0, 6))


def lit(rng):
    v = rng.choice(DOM + [-1, 6])
    t = rng.random()
    if t < 0.1:
        return f"{v}::int8"
    if t < 0.18:
        return f"{v}::int2"
    return str(v)


def atom(rng, cols):
    c = rng.choice(cols)
    x = rng.random()
    if x < 0.3:
        return f"{c} {rng.choice(['=', '<', '<=', '>', '>=', '<>'])} {lit(rng)}"
    if x < 0.4:
        return f"{c} IS {rng.choice(['NULL', 'NOT NULL'])}"
    if x < 0.55:
        vals = [str(rng.choice(DOM + [-1, 6])) for _ in range(rng.randint(0, 4))]
        if rng.random() < 0.15:
            vals.append("NULL")
        op = rng.choice(["=", "=", "<", ">", "<=", ">=", "<>"])
        q = rng.choice(["ANY", "ANY", "ALL"])
        return f"{c} {op} {q}('{{{','.join(vals)}}}'::{rng.choice(['int[]', 'int[]', 'int8[]'])})"
    if x < 0.62:
        return f"{c} BETWEEN {lit(rng)} AND {lit(rng)}"
    if x < 0.85:
        k = rng.randint(2, 3)
        cs = rng.sample(["a", "b", "c"], k) if rng.random() < 0.4 else ["a", "b", "c"][:k]
        vs = [lit(rng) for _ in range(k)]
        return f"({', '.join(cs)}) {rng.choice(['<', '<=', '>', '>=', '=', '<>'])} ({', '.join(vs)})"
    # redundant chain on one column
    return f"{c} > {lit(rng)} AND {c} >= {lit(rng)} AND {c} < {lit(rng)}"


def pred(rng):
    n = rng.randint(1, 4)
    parts = [atom(rng, ["a", "b", "c"]) for _ in range(n)]
    if rng.random() < 0.15:
        return "(" + " OR ".join(parts) + ")"
    return " AND ".join(parts)


MODES = {
    "SEQ": ["SET enable_indexscan=off", "SET enable_bitmapscan=off", "SET enable_indexonlyscan=off", "SET enable_seqscan=on"],
    "IDX": ["SET enable_seqscan=off", "SET enable_bitmapscan=off", "SET enable_indexonlyscan=off", "SET enable_indexscan=on"],
    "IOS": ["SET enable_seqscan=off", "SET enable_bitmapscan=off", "SET enable_indexscan=off", "SET enable_indexonlyscan=on"],
    "BMP": ["SET enable_seqscan=off", "SET enable_indexscan=off", "SET enable_indexonlyscan=off", "SET enable_bitmapscan=on"],
}


def main():
    port, seed, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    verbose = "--verbose" in sys.argv
    outdir = os.path.expanduser("~/audit/fuzz/out-ix")
    os.makedirs(outdir, exist_ok=True)
    db = f"ixf_{seed}"
    with psycopg.connect(f"host=/tmp port={port} user=postgres dbname=postgres", autocommit=True) as c0:
        c0.execute(f"DROP DATABASE IF EXISTS {db} WITH (FORCE)")
        c0.execute(f"CREATE DATABASE {db}")
    conn = psycopg.connect(f"host=/tmp port={port} user=postgres dbname={db}", autocommit=True)
    conn.prepare_threshold = None
    cur = conn.cursor()
    cur.execute("SET statement_timeout='20s'")
    st = {"tables": 0, "queries": 0, "ok": 0, "mismatch": 0, "error": 0}
    for i in range(n):
        rng = random.Random(seed * 104729 + i)
        cur.execute("DROP TABLE IF EXISTS t")
        cur.execute("CREATE TABLE t (id int, a int, b int, c int) WITH (autovacuum_enabled = off)")
        nrows = rng.choice([50, 300, 2000])
        nullp = rng.choice([0.0, 0.05, 0.2])
        rows = []
        for k in range(nrows):
            rows.append((k,) + tuple(None if rng.random() < nullp else rng.choice(DOM) for _ in range(3)))
        with cur.copy("COPY t FROM STDIN") as cp:
            for r in rows:
                cp.write_row(r)
        k = rng.randint(1, 3)
        icols = rng.sample(["a", "b", "c"], k)
        spec = ", ".join(f"{c}{rng.choice(['', ' DESC'])}{rng.choice(['', ' NULLS FIRST', ' NULLS LAST'])}" for c in icols)
        uniq = ""
        ddl = f"CREATE INDEX ti ON t ({spec})"
        cur.execute(ddl)
        cur.execute("VACUUM ANALYZE t")
        st["tables"] += 1
        for q in range(12):
            p = pred(rng)
            direction = rng.choice(["", " DESC"])
            nulls = rng.choice(["", " NULLS FIRST", " NULLS LAST"])
            order = ", ".join(f"{c}{direction}{nulls}" for c in icols)
            qs = {
                "rows": f"SELECT id FROM t WHERE {p}",
                "ord": f"SELECT {', '.join(icols)} FROM t WHERE {p} ORDER BY {order}",
            }
            for qk, sql in qs.items():
                res = {}
                try:
                    for m, sets in MODES.items():
                        if m == "IOS" and qk == "rows":
                            continue
                        for s_ in sets:
                            cur.execute(s_)
                        cur.execute(sql)
                        r = cur.fetchall()
                        res[m] = sorted(r, key=lambda x: tuple((v is None, v) for v in x)) if qk == "rows" else r
                    cur.execute("RESET ALL")
                    cur.execute("SET statement_timeout='20s'")
                except psycopg.Error as e:
                    st["error"] += 1
                    if verbose:
                        print("err", e.sqlstate, str(e).splitlines()[0], "|", sql)
                    cur.execute("RESET ALL")
                    continue
                st["queries"] += 1
                bad = [m for m in res if res[m] != res["SEQ"]]
                if not bad:
                    st["ok"] += 1
                    continue
                st["mismatch"] += 1
                fn = os.path.join(outdir, f"mismatch-s{seed}-{i}-{q}-{qk}.sql")
                with open(fn, "w") as f:
                    f.write(f"-- rows={nrows} nullp={nullp}\nCREATE TABLE t (id int, a int, b int, c int);\n")
                    f.write("INSERT INTO t VALUES " + ", ".join("(" + ", ".join("NULL" if v is None else str(v) for v in r) + ")" for r in rows) + ";\n")
                    f.write(ddl + ";\nVACUUM ANALYZE t;\n" + sql + ";\n")
                    f.write("/* " + json.dumps({m: len(v) for m, v in res.items()}) + f" bad={bad} */\n")
                if verbose:
                    print("MISMATCH", bad, fn)
    print(json.dumps({"seed": seed, **st}))


if __name__ == "__main__":
    main()
