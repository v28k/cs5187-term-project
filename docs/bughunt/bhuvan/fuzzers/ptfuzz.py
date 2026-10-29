"""Differential fuzzer for partition pruning.

Each case builds a random partitioned table "pt" (RANGE with 1-3 int keys and
MINVALUE/MAXVALUE bounds, LIST with NULLs, or HASH; optional DEFAULT and
sub-partitions), routes random rows into it, and copies the routed rows into a
plain heap table "pl".  Random predicates over the key columns are then run:

  REF   : plain table
  PLAN  : partitioned table, plan-time pruning
  GEN   : PREPARE with parameters, plan_cache_mode=force_generic_plan
          (initial/exec-time pruning)
  OFF   : partitioned table, enable_partition_pruning = off

All four must return the same multiset of row ids.

usage: ptfuzz.py PORT SEED N [--verbose]
"""
import json, os, random, sys
import psycopg

DOM = list(range(0, 8))


def tup_key(t):
    # MINVALUE < ints < MAXVALUE, lexicographic
    return tuple(-10**9 if x == "MINVALUE" else (10**9 if x == "MAXVALUE" else x) for x in t)


def lit(x):
    return str(x)


class Case:
    def __init__(self, rng):
        self.rng = rng
        self.ddl = []
        self.keys = []
        self.desc = ""

    def range_bounds(self, k, nparts):
        r = self.rng
        tuples = set()
        tries = 0
        while len(tuples) < nparts * 2 and tries < 500:
            tries += 1
            t = []
            for i in range(k):
                x = r.random()
                if i > 0 and x < 0.12:
                    t += ["MINVALUE"] * (k - i)
                    break
                if i > 0 and x < 0.24:
                    t += ["MAXVALUE"] * (k - i)
                    break
                if i == 0 and x < 0.06:
                    t += ["MINVALUE"] * k
                    break
                if i == 0 and x < 0.12:
                    t += ["MAXVALUE"] * k
                    break
                t.append(r.choice(DOM))
            tuples.add(tuple(t))
        ts = sorted(tuples, key=tup_key)
        pairs = []
        if r.random() < 0.5:
            # contiguous
            for i in range(len(ts) - 1):
                if len(pairs) >= nparts:
                    break
                pairs.append((ts[i], ts[i + 1]))
        else:
            for i in range(0, len(ts) - 1, 2):
                pairs.append((ts[i], ts[i + 1]))
        return pairs

    def fmt(self, t):
        return "(" + ", ".join(lit(x) for x in t) + ")"

    def make_table(self, name, depth=0, avail=("a", "b", "c")):
        r = self.rng
        strat = r.choice(["RANGE", "RANGE", "RANGE", "LIST", "HASH"]) if depth == 0 else r.choice(["RANGE", "LIST", "HASH"])
        if strat == "RANGE":
            k = r.choice([1, 2, 2, 3, 3]) if depth == 0 else r.choice([1, 2])
        elif strat == "HASH":
            k = r.choice([1, 2])
        else:
            k = 1
        k = min(k, len(avail))
        keys = r.sample(list(avail), k) if r.random() < 0.3 else list(avail)[:k]
        if depth == 0:
            self.ddl.append(f"CREATE TABLE {name} (id int, a int, b int, c int) PARTITION BY {strat} ({', '.join(keys)})")
        parts = []
        if strat == "RANGE":
            for (lo, hi) in self.range_bounds(k, r.randint(1, 5)):
                parts.append(f"FOR VALUES FROM {self.fmt(lo)} TO {self.fmt(hi)}")
        elif strat == "LIST":
            vals = r.sample(DOM, r.randint(2, 6))
            r.shuffle(vals)
            groups = []
            while vals:
                g = [vals.pop() for _ in range(min(len(vals), r.randint(1, 3)))]
                groups.append(g)
            if r.random() < 0.4:
                r.choice(groups).append("NULL")
            for g in groups:
                parts.append(f"FOR VALUES IN ({', '.join(lit(x) for x in g)})")
        else:
            mods = r.choice([[2, 2], [3, 3, 3], [2, 4, 4], [4, 4, 4, 4], [2, 4]])
            used = {}
            for m in mods:
                # pick remainder not overlapping: simple scheme, try all
                for rem in range(m):
                    ok = True
                    for (m2, r2) in used.items():
                        pass
                    key = (m, rem)
                    if key not in used:
                        used[key] = True
                        parts.append(f"FOR VALUES WITH (MODULUS {m}, REMAINDER {rem})")
                        break
        out = []
        for i, b in enumerate(parts):
            pname = f"{name}_{i}"
            sub = ""
            if depth == 0 and r.random() < 0.25:
                rest = [x for x in ("a", "b", "c") if x not in keys] or ["a", "b", "c"]
                subname = pname
                out.append((pname, b, True, rest))
            else:
                out.append((pname, b, False, None))
        has_default = strat != "HASH" and r.random() < 0.6
        for (pname, b, is_sub, rest) in out:
            if is_sub:
                sstrat = r.choice(["RANGE", "LIST"])
                skey = r.choice(rest)
                self.ddl.append(f"CREATE TABLE {pname} PARTITION OF {name} {b} PARTITION BY {sstrat} ({skey})")
                if sstrat == "RANGE":
                    for j, (lo, hi) in enumerate(self.range_bounds(1, r.randint(1, 3))):
                        self.ddl.append(f"CREATE TABLE {pname}_{j} PARTITION OF {pname} FOR VALUES FROM {self.fmt(lo)} TO {self.fmt(hi)}")
                else:
                    vals = r.sample(DOM, r.randint(1, 4))
                    for j, v in enumerate(vals):
                        self.ddl.append(f"CREATE TABLE {pname}_{j} PARTITION OF {pname} FOR VALUES IN ({v}{', NULL' if j == 0 and r.random() < 0.3 else ''})")
                if r.random() < 0.6:
                    self.ddl.append(f"CREATE TABLE {pname}_d PARTITION OF {pname} DEFAULT")
            else:
                self.ddl.append(f"CREATE TABLE {pname} PARTITION OF {name} {b}")
        if has_default:
            self.ddl.append(f"CREATE TABLE {name}_def PARTITION OF {name} DEFAULT")
        self.keys = keys
        self.strat = strat


class Pred:
    def __init__(self, rng):
        self.rng = rng
        self.params = []   # (type, value)

    def const(self, typ="int"):
        r = self.rng
        v = r.choice(DOM + [-1, 8, 9])
        if r.random() < 0.12:
            typ = r.choice(["int8", "int2"])
        self.params.append((typ, v))
        return (f"{v}::{typ}" if typ != "int" else str(v)), f"${len(self.params)}"

    def atom(self, cols):
        r = self.rng
        c = r.choice(cols)
        x = r.random()
        if x < 0.45:
            op = r.choice(["=", "=", "<", "<=", ">", ">=", "<>"])
            s, p = self.const()
            if r.random() < 0.15:
                comm = {"=": "=", "<": ">", "<=": ">=", ">": "<", ">=": "<=", "<>": "<>"}[op]
                return f"{s} {comm} {c}", f"{p} {comm} {c}"
            return f"{c} {op} {s}", f"{c} {op} {p}"
        if x < 0.55:
            t = r.choice(["IS NULL", "IS NOT NULL"])
            return f"{c} {t}", f"{c} {t}"
        if x < 0.7:
            n = r.randint(1, 3)
            items = [self.const() for _ in range(n)]
            nul = r.random() < 0.15
            neg = "NOT " if r.random() < 0.25 else ""
            s = ", ".join(i[0] for i in items) + (", NULL" if nul else "")
            p = ", ".join(i[1] for i in items) + (", NULL" if nul else "")
            return f"{c} {neg}IN ({s})", f"{c} {neg}IN ({p})"
        if x < 0.8:
            s1, p1 = self.const()
            s2, p2 = self.const()
            return f"{c} BETWEEN {s1} AND {s2}", f"{c} BETWEEN {p1} AND {p2}"
        if x < 0.9:
            vals = [r.choice(DOM) for _ in range(r.randint(0, 3))]
            if r.random() < 0.15:
                vals.append("NULL")
            arr = "'{" + ",".join(str(v) for v in vals) + "}'::int[]"
            self.params.append(("int[]", "{" + ",".join(str(v) for v in vals) + "}"))
            op = r.choice(["=", "<", ">", "<>", "<=", ">="])
            q = r.choice(["ANY", "ALL"])
            return f"{c} {op} {q}({arr})", f"{c} {op} {q}(${len(self.params)})"
        c2 = r.choice(cols)
        return f"{c} = {c2}", f"{c} = {c2}"

    def expr(self, cols, depth=0):
        r = self.rng
        if depth >= 2 or r.random() < 0.4:
            return self.atom(cols)
        n = r.randint(2, 3)
        subs = [self.expr(cols, depth + 1) for _ in range(n)]
        op = r.choice(["AND", "OR", "AND"])
        s = "(" + f" {op} ".join(x[0] for x in subs) + ")"
        p = "(" + f" {op} ".join(x[1] for x in subs) + ")"
        if r.random() < 0.1:
            return f"NOT {s}", f"NOT {p}"
        return s, p


def main():
    port, seed, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    verbose = "--verbose" in sys.argv
    outdir = os.path.expanduser("~/audit/fuzz/out-pt")
    os.makedirs(outdir, exist_ok=True)
    dbname = f"ptf_{seed}"
    with psycopg.connect(f"host=/tmp port={port} user=postgres dbname=postgres", autocommit=True) as c0:
        c0.execute(f"DROP DATABASE IF EXISTS {dbname} WITH (FORCE)")
        c0.execute(f"CREATE DATABASE {dbname}")
    conn = psycopg.connect(f"host=/tmp port={port} user=postgres dbname={dbname}", autocommit=True)
    conn.prepare_threshold = None   # no driver-side prepared statements
    cur = conn.cursor()
    cur.execute("SET statement_timeout='20s'")
    st = {"cases": 0, "queries": 0, "ok": 0, "mismatch": 0, "error": 0}
    for i in range(n):
        rng = random.Random(seed * 7919 + i)
        case = Case(rng)
        case.make_table("pt")
        cur.execute("DROP TABLE IF EXISTS pt, pl, src CASCADE")
        try:
            for d in case.ddl:
                cur.execute(d)
        except psycopg.Error as e:
            if verbose:
                print("ddl error", e.sqlstate, str(e).splitlines()[0])
            continue
        st["cases"] += 1
        rows = []
        for k in range(rng.randint(30, 120)):
            vals = [rng.choice(DOM + [-1, 8, 9]) if rng.random() > 0.1 else None for _ in range(3)]
            rows.append((k, *vals))
        cur.execute("CREATE TEMP TABLE src (id int, a int, b int, c int)")
        with cur.copy("COPY src FROM STDIN") as cp:
            for row in rows:
                cp.write_row(row)
        cur.execute("""DO $$ DECLARE r record; BEGIN
            FOR r IN SELECT * FROM src LOOP
              BEGIN INSERT INTO pt VALUES (r.id, r.a, r.b, r.c);
              EXCEPTION WHEN check_violation THEN NULL; END;
            END LOOP; END $$""")
        cur.execute("CREATE TABLE pl AS SELECT * FROM pt")
        cur.execute("ANALYZE pt; ANALYZE pl")
        for qn in range(15):
            pr = Pred(rng)
            s, p = pr.expr(["a", "b", "c"])
            ref = f"SELECT id FROM pl WHERE {s}"
            q = f"SELECT id FROM pt WHERE {s}"
            pq = f"SELECT id FROM pt WHERE {p}"
            types = ", ".join(t for t, v in pr.params)
            args = ", ".join((f"'{v}'" if t == "int[]" else str(v)) for t, v in pr.params)
            res = {}
            try:
                cur.execute(ref); res["REF"] = sorted(r[0] for r in cur.fetchall())
                cur.execute("SET enable_partition_pruning = on")
                cur.execute(q); res["PLAN"] = sorted(r[0] for r in cur.fetchall())
                if pr.params:
                    cur.execute(f"PREPARE gq({types}) AS {pq}")
                    try:
                        cur.execute("SET plan_cache_mode = force_generic_plan")
                        cur.execute(f"EXECUTE gq({args})"); res["GEN"] = sorted(r[0] for r in cur.fetchall())
                        cur.execute("RESET plan_cache_mode")
                    finally:
                        cur.execute("DEALLOCATE gq")
                cur.execute("SET enable_partition_pruning = off")
                cur.execute(q); res["OFF"] = sorted(r[0] for r in cur.fetchall())
                cur.execute("RESET enable_partition_pruning")
            except psycopg.Error as e:
                st["error"] += 1
                if verbose:
                    print("q error", e.sqlstate, str(e).splitlines()[0], "|", q)
                cur.execute("RESET ALL")
                continue
            st["queries"] += 1
            bad = [k for k in res if res[k] != res["REF"]]
            if not bad:
                st["ok"] += 1
                continue
            st["mismatch"] += 1
            fn = os.path.join(outdir, f"mismatch-s{seed}-{i}-{qn}.sql")
            with open(fn, "w") as f:
                f.write("\n".join(d + ";" for d in case.ddl) + "\n")
                f.write("INSERT INTO pt VALUES " + ", ".join(
                    "(" + ", ".join("NULL" if x is None else str(x) for x in r) + ")" for r in
                    [row for row in rows if row[0] in set(res['OFF'] + res['REF'])]) + ";\n" if res["REF"] else "")
                f.write(f"CREATE TABLE pl AS SELECT * FROM pt;\n-- REF\n{ref};\n-- PLAN/OFF\n{q};\n")
                if pr.params:
                    f.write(f"PREPARE gq({types}) AS {pq};\nSET plan_cache_mode = force_generic_plan;\nEXECUTE gq({args});\n")
                f.write("/* " + json.dumps({k: (len(v), v[:30]) for k, v in res.items()}) + " */\n")
            if verbose:
                print("MISMATCH", bad, fn)
        cur.execute("DROP TABLE IF EXISTS src")
    print(json.dumps({"seed": seed, **st}))


if __name__ == "__main__":
    main()
