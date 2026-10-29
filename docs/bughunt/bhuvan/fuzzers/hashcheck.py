"""Check hash-opclass invariants for every hash opclass type.

I1: x = y (opfamily equality)  =>  hash(x) = hash(y) and hash_ext(x,s) = hash_ext(y,s)
I2: low 32 bits of hash_ext(x, 0) = hash(x)            (xindex.sgml, support function 2)
I3: cross-type members of float_ops / integer_ops / text_ops agree on equal values
usage: hashcheck.py PORT
"""
import sys, itertools
import psycopg

V = {
 "int2": ["0", "-1", "1", "32767", "-32768", "255", "-256"],
 "int4": ["0", "-1", "1", "2147483647", "-2147483648", "65536"],
 "int8": ["0", "-1", "1", "9223372036854775807", "-9223372036854775808", "4294967296", "-4294967296", "2147483648"],
 "float4": ["0", "-0", "NaN", "Infinity", "-Infinity", "1.5", "1e-45", "3.4e38", "-1", "16777217"],
 "float8": ["0", "-0", "NaN", "Infinity", "-Infinity", "1.5", "4.9e-324", "1e308", "-1", "1e-45", "16777216"],
 "numeric": ["0", "-0", "0.0", "0.000", "-0.00", "1", "1.0", "1.00", "100", "1e2", "100.000", "NaN", "Infinity", "-Infinity",
             "1e-20", "0.00000000000000000001", "-1.0", "-1", "12345678901234567890.123", "1e1000", "10e999",
             "0.1e-500", "1e-501", "10000", "1e4", "9999.9999", "123456789012345678", "1.23456789012345678e17"],
 "interval": ["1 day", "24 hours", "1 mon", "30 days", "720 hours", "1 year", "12 mon", "360 days", "0", "-0 days",
              "infinity", "-infinity", "1 day -24 hours", "1 mon -30 days", "-1 mon 30 days", "1 mon 1 day", "31 days",
              "86400 seconds", "2592000 seconds", "1 microsecond", "-1 microsecond", "178000000 years", "-178000000 years",
              "1 mon -1 microsecond", "29 days 24 hours"],
 "timetz": ["00:00+00", "01:00+01", "24:00+00", "00:00-00", "12:00+14", "23:59:59.999999-15:59", "00:00+15:59", "13:00+01", "12:00+00"],
 "time": ["00:00", "24:00", "23:59:59.999999", "12:00"],
 "timestamp": ["infinity", "-infinity", "2000-01-01", "epoch", "294276-12-31 23:59:59.999999", "4713-01-01 00:00 BC"],
 "timestamptz": ["infinity", "-infinity", "2000-01-01 00:00+00", "2000-01-01 01:00+01", "epoch", "294276-12-31 23:59:59.999999+00"],
 "date": ["infinity", "-infinity", "2000-01-01", "epoch", "5874897-12-31", "4713-01-01 BC"],
 "bpchar": ["a", "a ", "a  ", "", " ", "  ", "ab", "ab ", "A"],
 "text": ["a", "a ", "", "A", "ab"],
 "name": ["a", "a ", "", "A", "ab"],
 "bytea": ["\\x", "\\x00", "\\x0000", "\\xff"],
 "jsonb": ["1", "1.0", "1.00", "-0", "0", "0.0", "1e2", "100", "\"a\"", "{\"a\":1}", "{\"a\":1.0}", "[1]", "[1.0]", "[]", "{}",
           "null", "true", "false", "[1,2]", "[2,1]", "{\"a\":{\"b\":1.10}}", "{\"a\":{\"b\":1.1}}", "1e1000", "10e999",
           "[[]]", "[{}]", "\"\"", "[null]", "{\"a\":null}", "-1.0", "-1", "{\"b\":1,\"a\":2}", "{\"a\":2,\"b\":1}"],
 "inet": ["1.2.3.4", "1.2.3.4/32", "1.2.3.4/24", "::ffff:1.2.3.4", "0.0.0.0/0", "::/0", "1.2.3.0/24", "::1", "::1/128"],
 "macaddr": ["08:00:2b:01:02:03", "08-00-2b-01-02-03", "0800.2b01.0203"],
 "macaddr8": ["08:00:2b:01:02:03", "08:00:2b:ff:fe:01:02:03", "08:00:2b:01:02:03:04:05"],
 "uuid": ["00000000-0000-0000-0000-000000000000", "ffffffff-ffff-ffff-ffff-ffffffffffff", "A0EEBC99-9C0B-4EF8-BB6D-6BB9BD380A11", "a0eebc999c0b4ef8bb6d6bb9bd380a11"],
 "oid": ["0", "1", "4294967295", "-1", "2147483648"],
 "oid8": ["0", "1", "4294967295", "18446744073709551615", "4294967296", "9223372036854775808"],
 "xid": ["0", "1", "4294967295"],
 "xid8": ["0", "1", "4294967295", "4294967296", "18446744073709551615"],
 "cid": ["0", "1", "4294967295"],
 "pg_lsn": ["0/0", "FFFFFFFF/FFFFFFFF", "1/0", "0/1"],
 "oidvector": ["1 2", "1  2", "", "4294967295"],
 "tid": ["(0,1)", "(4294967295,65535)", "(0,0)"],
 "bool": ["t", "f", "yes", "off"],
 "char": ["a", "", "\\377"],
 "int4[]": ["{1,2}", "[0:1]={1,2}", "{}", "{NULL}", "{{1,2}}", "{1,NULL}", "[1:2]={1,2}"],
 "numeric[]": ["{1.0,2}", "{1,2.00}", "{NaN}", "{NaN,NULL}", "{1e2}", "{100.0}", "{}"],
 "float8[]": ["{0}", "{-0}", "{NaN}", "{-NaN}"],
 "jsonb[]": ["{1}", "{1.0}"],
 "interval[]": ["{\"1 day\"}", "{\"24 hours\"}"],
 "numrange": ["[1.0,2.0)", "[1.00,2.000)", "empty", "[1,1)", "(,)", "(,1.0]", "(,1]", "[NaN,NaN]", "[1e2,1e3)", "[100,1000.0)"],
 "int4range": ["[1,3)", "[1,2]", "(0,3)", "empty", "[1,1)", "(,)", "(,3)", "(,2]"],
 "daterange": ["[2000-01-01,2000-01-03)", "[2000-01-01,2000-01-02]", "(,infinity)", "[-infinity,infinity]", "empty"],
 "tstzrange": ["[2000-01-01 00:00+00,2000-01-02 00:00+00)", "[2000-01-01 01:00+01,2000-01-02 01:00+01)", "empty"],
 "nummultirange": ["{[1.0,2.0)}", "{[1.00,2.00)}", "{}", "{empty}", "{[1,2),[2,3)}", "{[1,3)}", "{[NaN,NaN]}"],
 "int4multirange": ["{[1,2),[2,3)}", "{[1,3)}", "{[1,2],[3,3]}", "{}", "{empty,empty}"],
 "ctype": ["(1.0,a)", "(1.00,a)", "(,)", "(1e2,\"b\")", "(100,b)", "(NaN,)"],
 "etype": ["x", "y"],
}

CROSS = [("int2", "int4"), ("int2", "int8"), ("int4", "int8"), ("float4", "float8"), ("text", "name")]


def main():
    port = int(sys.argv[1])
    conn = psycopg.connect(f"host=/tmp port={port} user=postgres dbname=postgres", autocommit=True)
    conn.prepare_threshold = None
    cur = conn.cursor()
    cur.execute("DROP TYPE IF EXISTS ctype, etype")
    cur.execute("CREATE TYPE ctype AS (n numeric, t text)")
    cur.execute("CREATE TYPE etype AS ENUM ('x', 'y')")
    problems = 0
    for typ, lits in V.items():
        # find the hash support procs of the type's default hash opclass
        cur.execute("""
            SELECT p1.amproc::regproc::text, p2.amproc::regproc::text, o.amopopr::regoperator::text
            FROM pg_opclass c JOIN pg_am a ON a.oid = c.opcmethod AND a.amname = 'hash'
            JOIN pg_amproc p1 ON p1.amprocfamily = c.opcfamily AND p1.amprocnum = 1 AND p1.amproclefttype = c.opcintype
            LEFT JOIN pg_amproc p2 ON p2.amprocfamily = c.opcfamily AND p2.amprocnum = 2 AND p2.amproclefttype = c.opcintype
            JOIN pg_amop o ON o.amopfamily = c.opcfamily AND o.amoplefttype = c.opcintype AND o.amoprighttype = c.opcintype
            WHERE c.opcdefault AND (c.opcintype = %s::regtype OR
                  (c.opcintype = 'anyarray'::regtype AND %s::regtype::text LIKE '%%[]') OR
                  (c.opcintype = 'anyrange'::regtype AND EXISTS (SELECT 1 FROM pg_range WHERE rngtypid = %s::regtype)) OR
                  (c.opcintype = 'anymultirange'::regtype AND EXISTS (SELECT 1 FROM pg_range WHERE rngmultitypid = %s::regtype)) OR
                  (c.opcintype = 'record'::regtype AND %s = 'ctype') OR
                  (c.opcintype = 'anyenum'::regtype AND %s = 'etype'))
            ORDER BY (c.opcintype = %s::regtype) DESC LIMIT 1""", (typ, typ, typ, typ, typ, typ, typ))
        row = cur.fetchone()
        if not row:
            print(f"!! no hash opclass found for {typ}")
            continue
        h1, h2, eqop = row
        vals = []
        for l in lits:
            try:
                cur.execute(f"SELECT %s::{typ}", (l,))
                vals.append(l)
            except psycopg.Error as e:
                print(f"   skip {typ} literal {l!r}: {str(e).splitlines()[0]}")
        # I2
        if h2:
            for l in vals:
                cur.execute(f"SELECT {h1}(%s::{typ}), ({h2}(%s::{typ}, 0) & 4294967295)::bigint, ({h1}(%s::{typ})::bigint & 4294967295)",
                            (l, l, l))
                a, b, c = cur.fetchone()
                if b != c:
                    problems += 1
                    print(f"I2 VIOLATION {typ} {l!r}: hash={a} low32(ext0)={b}")
        # I1
        for x, y in itertools.combinations_with_replacement(vals, 2):
            cur.execute(f"SELECT (%s::{typ}) = (%s::{typ})", (x, y))
            eq = cur.fetchone()[0]
            if not eq:
                continue
            cur.execute(f"SELECT {h1}(%s::{typ}) = {h1}(%s::{typ})" +
                        (f", {h2}(%s::{typ}, 12345) = {h2}(%s::{typ}, 12345)" if h2 else ", true"),
                        (x, y, x, y) if h2 else (x, y))
            s1, s2 = cur.fetchone()
            if not (s1 and s2):
                problems += 1
                print(f"I1 VIOLATION {typ}: {x!r} = {y!r} but hash equal={s1} ext equal={s2}")
        print(f"ok {typ:16s} {h1}/{h2} values={len(vals)}")
    for t1, t2 in CROSS:
        for x in V[t1]:
            for y in V[t2]:
                try:
                    cur.execute(f"SELECT %s::{t1} = %s::{t2}, hash_{'' if False else ''}x", (x, y))
                except psycopg.Error:
                    pass
    # cross-type: use the family procs explicitly
    fam = {"int2": ("hashint2", "hashint2extended"), "int4": ("hashint4", "hashint4extended"), "int8": ("hashint8", "hashint8extended"),
           "float4": ("hashfloat4", "hashfloat4extended"), "float8": ("hashfloat8", "hashfloat8extended"),
           "text": ("hashtext", "hashtextextended"), "name": ("hashname", "hashnameextended")}
    for t1, t2 in CROSS:
        for x in V[t1]:
            for y in V[t2]:
                try:
                    cur.execute(f"SELECT %s::{t1} = %s::{t2}", (x, y))
                except psycopg.Error:
                    continue
                if not cur.fetchone()[0]:
                    continue
                a1, a2 = fam[t1]; b1, b2 = fam[t2]
                cur.execute(f"SELECT {a1}(%s::{t1}) = {b1}(%s::{t2}), {a2}(%s::{t1}, 99) = {b2}(%s::{t2}, 99)", (x, y, x, y))
                s1, s2 = cur.fetchone()
                if not (s1 and s2):
                    problems += 1
                    print(f"I3 VIOLATION {t1}/{t2}: {x!r} = {y!r} hash={s1} ext={s2}")
    print("problems:", problems)


if __name__ == "__main__":
    main()
