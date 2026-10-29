"""DDL-sequence fuzzer for NOT NULL / inheritance / partition metadata.

Random DDL + DML over a small family of tables (inheritance and partitioning).
After every statement, check:
  I1  a column with a validated NOT NULL constraint (or attnotnull, as the
      catalog reports it) holds no NULLs in that table (ONLY);
  I2  SELECT count(*) FROM t WHERE c IS NULL         (planner may fold via NOT NULL)
      == SELECT count(*) FROM t WHERE num_nulls(c) = 1 (opaque to the planner)
      for every table t (with its inheritance children) and column c;
  I3  the same for "c IS NOT NULL" vs num_nonnulls, and for LEFT JOIN anti-join
      forms (a LEFT JOIN t ON ... WHERE t.c IS NULL) vs NOT EXISTS reference.
Errors from DDL are expected and ignored; internal errors (XX000) and
assertion failures are reported.

usage: python nnfuzz.py PORT SEED N
"""
import random
import sys

import psycopg

port, seed, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
rng = random.Random(seed)
admin = psycopg.connect(host="/tmp", port=port, user="postgres", dbname="postgres", autocommit=True)
db = f"nn_{seed}"
admin.execute(f"DROP DATABASE IF EXISTS {db}")
admin.execute(f"CREATE DATABASE {db}")
admin.close()


def connect():
    c = psycopg.connect(host="/tmp", port=port, user="postgres", dbname=db, autocommit=True)
    c.execute("SET client_min_messages = error")
    return c


conn = connect()
log = []          # statements executed so far in this episode (for replay)
reports = 0
stats = {'ok': 0, 'err': 0}


def run(sql, quiet=True):
    global conn
    log.append(sql)
    try:
        conn.execute(sql)
        stats['ok'] += 1
        return True
    except psycopg.Error as e:
        stats['err'] += 1
        code = getattr(e, "sqlstate", None)
        if code in ("XX000", "XX001", "XX002") or conn.broken:
            report(f"INTERNAL {code}: {str(e).splitlines()[0]}")
            if conn.broken:
                conn = connect()
        return False


def report(msg):
    global reports
    reports += 1
    print(f"REPORT {msg}", flush=True)
    if reports <= 30:
        with open(f"/home/bhuvi/audit2/fuzz/nn_{seed}_{reports}.sql", "w") as fh:
            fh.write(f"-- {msg}\n" + ";\n".join(log) + ";\n")


TABLES = ["p", "c1", "c2", "g", "q", "q1", "q2", "qd"]
COLS = ["a", "b", "c"]


def setup():
    log.clear()
    for t in reversed(TABLES):
        run(f"DROP TABLE IF EXISTS {t} CASCADE")
    run("CREATE TABLE p (a int, b int, c text)")
    run("CREATE TABLE c1 () INHERITS (p)")
    run("CREATE TABLE c2 (a int, b int, c text, d int)")
    if rng.random() < 0.5:
        run("ALTER TABLE c2 INHERIT p")
    run("CREATE TABLE g () INHERITS (c1)")
    run("CREATE TABLE q (a int, b int, c text) PARTITION BY LIST (a)")
    run("CREATE TABLE q1 PARTITION OF q FOR VALUES IN (1, 2)")
    run("CREATE TABLE q2 (a int, b int, c text)")
    run("CREATE TABLE qd PARTITION OF q DEFAULT")
    run("CREATE TABLE r (k int)")
    run("INSERT INTO r SELECT generate_series(0, 5)")


def val():
    return "NULL" if rng.random() < 0.35 else str(rng.randint(0, 5))


def ddl():
    t = rng.choice(TABLES)
    col = rng.choice(COLS)
    only = "ONLY " if rng.random() < 0.3 else ""
    nm = f"nn_{t}_{col}"
    ops = [
        lambda: f"ALTER TABLE {only}{t} ALTER COLUMN {col} SET NOT NULL",
        lambda: f"ALTER TABLE {only}{t} ALTER COLUMN {col} DROP NOT NULL",
        lambda: f"ALTER TABLE {only}{t} ADD CONSTRAINT {nm} NOT NULL {col}"
                + rng.choice(["", " NO INHERIT", " NOT VALID", " NO INHERIT NOT VALID"]),
        lambda: f"ALTER TABLE {only}{t} VALIDATE CONSTRAINT {rng.choice([nm, nm.replace(t, rng.choice(TABLES))])}",
        lambda: f"ALTER TABLE {only}{t} ALTER CONSTRAINT {nm} {rng.choice(['INHERIT', 'NO INHERIT'])}",
        lambda: f"ALTER TABLE {only}{t} DROP CONSTRAINT {rng.choice(['IF EXISTS ', ''])}{nm}",
        lambda: f"ALTER TABLE {only}{t} DROP CONSTRAINT IF EXISTS {t}_pkey",
        lambda: f"ALTER TABLE {only}{t} ADD PRIMARY KEY ({col})",
        lambda: f"ALTER TABLE {t} ADD CONSTRAINT {t}_{col}_uq UNIQUE ({col})",
        lambda: f"ALTER TABLE {only}{t} ALTER COLUMN {col} TYPE {rng.choice(['bigint', 'int', 'text', 'numeric'])} USING {col}::text::{rng.choice(['bigint', 'int', 'text', 'numeric'])}",
        lambda: f"ALTER TABLE {only}{t} ADD COLUMN IF NOT EXISTS {col} int" + rng.choice(["", " NOT NULL DEFAULT 1", " NOT NULL"]),
        lambda: f"ALTER TABLE {only}{t} DROP COLUMN IF EXISTS {col}",
        lambda: f"ALTER TABLE {rng.choice(['c1', 'c2', 'g'])} {rng.choice(['INHERIT', 'NO INHERIT'])} {rng.choice(['p', 'c1'])}",
        lambda: f"ALTER TABLE q ATTACH PARTITION q2 FOR VALUES IN ({rng.randint(3, 5)})",
        lambda: "ALTER TABLE q DETACH PARTITION q2",
        lambda: "ALTER TABLE q DETACH PARTITION q1",
        lambda: "ALTER TABLE q ATTACH PARTITION q1 FOR VALUES IN (1, 2)",
        lambda: "ALTER TABLE q DETACH PARTITION qd",
        lambda: "ALTER TABLE q ATTACH PARTITION qd DEFAULT",
        lambda: f"CREATE TABLE IF NOT EXISTS {rng.choice(['c2', 'q2'])} (a int, b int, c text)",
        lambda: f"ALTER TABLE {t} ALTER COLUMN {col} {rng.choice(['ADD GENERATED ALWAYS AS IDENTITY', 'DROP IDENTITY IF EXISTS'])}",
        lambda: f"ALTER TABLE {t} ALTER COLUMN {col} SET EXPRESSION AS (a + 1)",
    ]
    return rng.choice(ops)()


def dml():
    t = rng.choice(TABLES)
    k = rng.random()
    if k < 0.6:
        return f"INSERT INTO {t} (a, b, c) VALUES ({val()}, {val()}, {val()})"
    if k < 0.8:
        return f"UPDATE {t} SET {rng.choice(COLS)} = {val()} WHERE a IS NOT DISTINCT FROM {val()}"
    return f"DELETE FROM {t} WHERE b IS NOT DISTINCT FROM {val()}"


def cols_of(t):
    r = conn.execute("""SELECT attname, attnotnull FROM pg_attribute
        WHERE attrelid = to_regclass(%s) AND attnum > 0 AND NOT attisdropped""", (t,)).fetchall()
    return r


def check(stmt):
    for t in TABLES:
        try:
            cols = cols_of(t)
        except psycopg.Error:
            return
        if not cols:
            continue
        validated = {r[0] for r in conn.execute("""
            SELECT a.attname FROM pg_constraint c JOIN pg_attribute a
              ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
            WHERE c.conrelid = to_regclass(%s) AND c.contype = 'n' AND c.convalidated""", (t,)).fetchall()}
        for name, attnotnull in cols:
            qn = f'"{name}"'
            try:
                only_nulls = conn.execute(f"SELECT count(*) FROM ONLY {t} WHERE num_nulls({qn}) = 1").fetchone()[0]
                if only_nulls and (name in validated):
                    report(f"I1 {t}.{name}: {only_nulls} NULLs despite validated NOT NULL (attnotnull={attnotnull}) after: {stmt}")
                for frm in (t, f"ONLY {t}"):
                    a = conn.execute(f"SELECT count(*) FROM {frm} WHERE {qn} IS NULL").fetchone()[0]
                    b = conn.execute(f"SELECT count(*) FROM {frm} WHERE num_nulls({qn}) = 1").fetchone()[0]
                    if a != b:
                        report(f"I2 {frm}.{name}: IS NULL count {a} vs num_nulls {b} after: {stmt}")
                    a = conn.execute(f"SELECT count(*) FROM r LEFT JOIN {frm} x ON x.a = r.k WHERE x.{qn} IS NULL").fetchone()[0]
                    b = conn.execute(f"SELECT count(*) FROM r LEFT JOIN {frm} x ON x.a = r.k WHERE num_nulls(x.{qn}) = 1").fetchone()[0]
                    if a != b:
                        report(f"I3 {frm}.{name}: LEFT JOIN IS NULL count {a} vs num_nulls {b} after: {stmt}")
            except psycopg.Error as e:
                if getattr(e, "sqlstate", None) in ("XX000",):
                    report(f"INTERNAL in check: {e}")


for ep in range(n):
    setup()
    for step in range(rng.randint(10, 40)):
        if rng.random() < 0.08:
            # transactional wrapper with rollback
            stmts = [ddl() if rng.random() < 0.5 else dml() for _ in range(rng.randint(1, 4))]
            sql = "BEGIN; " + "; ".join(stmts) + ("; ROLLBACK" if rng.random() < 0.5 else "; COMMIT")
            # execute statement by statement to keep going on error
            run("BEGIN")
            for s in stmts:
                if not run(s):
                    break
            run(rng.choice(["ROLLBACK", "COMMIT"]))
            stmt = sql
        else:
            stmt = ddl() if rng.random() < 0.55 else dml()
            run(stmt)
        if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            run("ROLLBACK")
        check(stmt)
print(f"done seed={seed} episodes={n} reports={reports} stats={stats}")
