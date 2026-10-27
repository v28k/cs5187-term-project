"""Differential fuzzer for window functions with IGNORE NULLS (PG19+).

Oracle: the aggregate path of the same WindowAgg.
  first_value(e) IGNORE NULLS OVER w  == (array_agg(e) FILTER (WHERE e IS NOT NULL) OVER w)[1]
  last_value(e)  IGNORE NULLS OVER w  == a[cardinality(a)]
  nth_value(e,n) IGNORE NULLS OVER w  == a[n]
  lag(e,k,d)  IGNORE NULLS OVER (... ORDER BY o, id) == coalesce(a_prev[card-k+1], d)
      with a_prev over ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
  lead(e,k,d) IGNORE NULLS likewise with ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING

usage: python winfuzz.py PORT SEED N
"""
import random
import sys

import psycopg

port, seed, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
rng = random.Random(seed)
conn = psycopg.connect(host="/tmp", port=port, user="postgres", dbname="postgres", autocommit=True)
cur = conn.cursor()
dbname = f"wf_{seed}"
cur.execute(f"DROP DATABASE IF EXISTS {dbname}")
cur.execute(f"CREATE DATABASE {dbname}")
conn.close()
conn = psycopg.connect(host="/tmp", port=port, user="postgres", dbname=dbname, autocommit=True)
cur = conn.cursor()

ARGS = ["x", "x + 0", "CASE WHEN x % 3 = 0 THEN NULL ELSE x END",
        "nullif(x, o)", "(x * (1 + 0 * random()))::int", "x::text"]


def make_table():
    nrows = rng.choice([0, 1, 2, 5, 10, 20, 40, 150, 400])
    pnull = rng.choice([0.0, 0.3, 0.6, 0.9, 1.0])
    np_ = rng.choice([1, 2, 4])
    no = rng.choice([1, 3, 8, 1000])
    rows = []
    for i in range(nrows):
        x = None if rng.random() < pnull else rng.randint(-5, 50)
        o = None if rng.random() < 0.05 else rng.randint(0, no)
        rows.append((i, rng.randint(0, np_ - 1), o, x))
    cur.execute("DROP TABLE IF EXISTS w")
    cur.execute("CREATE TABLE w (id int, p int, o int, x int)")
    if rows:
        cur.executemany("INSERT INTO w VALUES (%s,%s,%s,%s)", rows)
    cur.execute("ANALYZE w")
    return rows


def bound(kind):
    c = rng.choice(["UNBOUNDED PRECEDING", "k PRECEDING", "CURRENT ROW",
                    "k FOLLOWING", "UNBOUNDED FOLLOWING"])
    if c.startswith("k"):
        c = f"{rng.randint(0, 3)}{c[1:]}"
    return c


def frame():
    mode = rng.choice(["", "ROWS", "RANGE", "GROUPS"])
    if not mode:
        return ""
    order = ["UNBOUNDED PRECEDING", "PRECEDING", "CURRENT ROW", "FOLLOWING", "UNBOUNDED FOLLOWING"]
    for _ in range(50):
        s, e = bound(mode), bound(mode)
        if s == "UNBOUNDED FOLLOWING" or e == "UNBOUNDED PRECEDING":
            continue
        rank = lambda b: order.index(b) if b in order else order.index(b.split(" ", 1)[1])
        if rank(s) > rank(e):
            continue
        break
    excl = rng.choice(["", "", " EXCLUDE CURRENT ROW", " EXCLUDE GROUP", " EXCLUDE TIES", " EXCLUDE NO OTHERS"])
    return f"{mode} BETWEEN {s} AND {e}{excl}"


def window():
    part = rng.choice(["", "PARTITION BY p "])
    ordk = rng.choice(["", "o", "o DESC", "o NULLS FIRST", "o DESC NULLS LAST", "o, id"])
    fr = frame()
    if "RANGE" in fr and ("PRECEDING" in fr or "FOLLOWING" in fr) and any(ch.isdigit() for ch in fr):
        if ordk in ("", "o, id"):
            ordk = "o"
    if fr.startswith("GROUPS") and not ordk:
        ordk = "o"
    if fr.startswith("RANGE") and not ordk and any(ch.isdigit() for ch in fr):
        ordk = "o"
    o = f"ORDER BY {ordk} " if ordk else ""
    return f"{part}{o}{fr}".strip()


def query():
    w = window()
    sel, chk = [], []
    nf = rng.randint(1, 4)
    for i in range(nf):
        a = rng.choice(ARGS)
        f = rng.choice(["first", "last", "nth", "lag", "lead"])
        agg = f"array_agg({a}) FILTER (WHERE ({a}) IS NOT NULL)"
        if f in ("first", "last", "nth"):
            if f == "first":
                e, oexp = f"first_value({a}) IGNORE NULLS OVER w", f"({agg} OVER w)[1]"
            elif f == "last":
                e, oexp = f"last_value({a}) IGNORE NULLS OVER w", f"(SELECT a[cardinality(a)] FROM (SELECT {agg} OVER w) s(a))"
                oexp = f"(({agg} OVER w))[cardinality(({agg} OVER w))]"
            else:
                k = rng.randint(1, 4)
                e, oexp = f"nth_value({a}, {k}) IGNORE NULLS OVER w", f"({agg} OVER w)[{k}]"
        else:
            part = "PARTITION BY p " if "PARTITION" in w else ""
            k = rng.choice([1, 1, 2, 3])
            d = rng.choice(["", ", NULL", ", -1"])
            dd = d[2:] if d else "NULL"
            if a == "x::text" and d == ", -1":
                d, dd = ", '-1'", "'-1'"
            lw = f"({part}ORDER BY o, id)"
            if f == "lag":
                e = f"lag({a}, {k}{d}) IGNORE NULLS OVER {lw}"
                fw = f"({part}ORDER BY o, id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)"
                oexp = f"coalesce(({agg} OVER {fw})[cardinality(({agg} OVER {fw}))-{k}+1], {dd})"
            else:
                e = f"lead({a}, {k}{d}) IGNORE NULLS OVER {lw}"
                fw = f"({part}ORDER BY o, id ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING)"
                oexp = f"coalesce(({agg} OVER {fw})[{k}], {dd})"
            # cardinality-k+1 may be <=0 -> NULL index -> NULL; fine
        sel.append(f"{e} AS f{i}")
        sel.append(f"{oexp} AS o{i}")
        chk.append(i)
    q = f"SELECT id, {', '.join(sel)} FROM w WINDOW w AS ({w}) ORDER BY id"
    return q, chk


mism = 0
errs = {}
for it in range(n):
    if it % 50 == 0:
        rows = make_table()
        settings = rng.choice(["RESET work_mem", "SET work_mem = '64kB'"])
        cur.execute(settings)
    q, chk = query()
    try:
        cur.execute(q)
        res = cur.fetchall()
    except psycopg.Error as ex:
        msg = str(ex).splitlines()[0]
        key = msg[:80]
        if key not in errs:
            errs[key] = q
            print("ERROR", msg, "\n   ", q, flush=True)
        if conn.closed or conn.broken:
            print("CONNECTION LOST", q, flush=True)
            break
        continue
    for r in res:
        for i in chk:
            f, o = r[1 + 2 * i], r[2 + 2 * i]
            if f != o and not (f is not None and o is not None and str(f) == str(o)):
                mism += 1
                if mism <= 20:
                    print(f"MISMATCH id={r[0]} f{i}={f!r} oracle={o!r}\n    {settings}; {q}", flush=True)
                    with open(f"/home/bhuvi/audit2/fuzz/mism_{seed}_{it}.sql", "w") as fh:
                        fh.write(f"-- seed {seed} it {it}\n{settings};\n")
                        cur.execute("SELECT string_agg(format('(%s,%s,%s,%s)', id, coalesce(p::text,'NULL'), coalesce(o::text,'NULL'), coalesce(x::text,'NULL')), ',') FROM w")
                        fh.write(f"CREATE TABLE w (id int, p int, o int, x int);\nINSERT INTO w VALUES {cur.fetchone()[0]};\n{q};\n")
                break
print(f"done seed={seed} n={n} mismatches={mism} distinct_errors={len(errs)}")
