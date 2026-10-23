import sys, psycopg

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5433
conn = psycopg.connect(f"host=localhost port={port} user=postgres dbname=postgres", autocommit=True)

V = {
 "tsquery": ["''", "'a'", "'!a'", "'a & !b'", "'a <-> b'", "'a <0> b'", "'!!a'", "'a:*'", "'a:AB'", "'(a|b)&c'", "'!(a <-> b)'", "'a <16384> b'"],
 "tsvector": ["''", "'a'", "'a:1'", "'a:1A b:2,3C'", "'a:16383'", "'\\'\\''"],
 "jsonb": ["'null'", "'[]'", "'{}'", "'\"\"'", "'1e1000'", "'-0'", "'[[[]]]'", "'{\"a\":{\"b\":[1,null]}}'", "'0.0'", "'\"\\u0000\"'"],
 "json": ["'  {\"a\" : 1, \"a\":2} '", "'[]'"],
 "jsonpath": ["'$'", "'strict $.a'", "'$ ? (@ like_regex \"a\" flag \"i\")'", "'$.a[*] ? (@ > 1)'", "'last'", "'$.datetime()'", "'$.a.b.c[1 to last]'", "'$.\"\"'", "'$ ? (exists (@.a))'", "'-$'", "'$.decimal(4,2)'", "'$.string()'", "'$[*].keyvalue()'"],
 "numeric": ["'NaN'", "'Infinity'", "'-Infinity'", "'0'", "'-0'", "'0.000'", "'1e-1000'", "'123456789012345678901234567890.123'", "'0.1e-16383'"],
 "float4": ["'NaN'", "'-0'", "'1e-45'", "'Infinity'"],
 "float8": ["'NaN'", "'-0'", "'5e-324'", "'-Infinity'"],
 "interval": ["'infinity'", "'-infinity'", "'0'", "'-178000000 years'", "'1 mon -1 day 1 us'"],
 "date": ["'infinity'", "'-infinity'", "'4713-01-01 BC'", "'5874897-12-31'"],
 "timestamp": ["'infinity'", "'-infinity'", "'4713-01-01 00:00 BC'", "'294276-12-31 23:59:59.999999'"],
 "timestamptz": ["'infinity'", "'4713-01-01 00:00 BC'"],
 "time": ["'24:00'", "'00:00'"],
 "timetz": ["'24:00-15:59'", "'00:00+15:59'"],
 "int4range": ["'empty'", "'(,)'", "'[1,2)'", "'(1,)'"],
 "numrange": ["'empty'", "'[NaN,NaN]'", "'(-Infinity,Infinity)'", "'[1,1]'"],
 "tstzrange": ["'[-infinity,infinity]'", "'empty'"],
 "int4multirange": ["'{}'", "'{empty}'", "'{(,)}'", "'{[1,2),[3,4)}'"],
 "nummultirange": ["'{}'", "'{[NaN,NaN]}'"],
 "int4[]": ["'{}'", "'{NULL}'", "'[0:1]={1,2}'", "'{{}}'", "'[-2147483648:-2147483647]={1,2}'"],
 "text[]": ["'{\"\"}'", "'{{a,b},{c,d}}'"],
 "inet": ["'::/0'", "'0.0.0.0/0'", "'::ffff:1.2.3.4'", "'1.2.3.4/32'", "'fe80::1%eth0'"],
 "cidr": ["'::/0'", "'0.0.0.0/0'", "'10/8'"],
 "macaddr8": ["'08:00:2b:01:02:03:04:05'", "'08002b010203'"],
 "bit varying": ["''", "'1'", "B'101010101'"],
 "bit(3)": ["'101'"],
 "point": ["'(NaN,NaN)'", "'(-0,0)'", "'(Infinity,-Infinity)'"],
 "line": ["'{1,0,0}'", "'{0,1,NaN}'"],
 "lseg": ["'[(0,0),(0,0)]'"],
 "box": ["'(0,0),(0,0)'", "'(NaN,1),(2,3)'"],
 "path": ["'[(0,0)]'", "'((0,0),(1,1))'"],
 "polygon": ["'((0,0))'", "'((0,0),(1,1),(NaN,1))'"],
 "circle": ["'<(0,0),0>'", "'<(1,1),Infinity>'"],
 "money": ["'-92233720368547758.08'"],
 "xml": ["'<a/>'", "''", "'text only'", "'<?xml version=\"1.0\"?><a/>'"],
 "uuid": ["'00000000-0000-0000-0000-000000000000'"],
 "pg_lsn": ["'FFFFFFFF/FFFFFFFF'"],
 "txid_snapshot": ["'10:20:'", "'10:20:10,11'"],
 "pg_snapshot": ["'10:20:'", "'10:20:10,11'"],
 "oidvector": ["''", "'1 2 3'"],
 "int2vector": ["''", "'1 2'"],
 "aclitem": ["'=r/postgres'"],
 "regtype": ["'int4'", "'-'"],
 "regclass": ["'-'"],
 "\"char\"": ["''", "'\\377'"],
 "name": ["''"],
 "bytea": ["''", "'\\x00'"],
 "tid": ["'(4294967295,65535)'"],
 "xid8": ["'18446744073709551615'"],
 "record": ["row()", "row(1,NULL)", "row(row())"],
 "gtsvector": [],
}
fails = 0
for typ, lits in V.items():
    for lit in lits:
        expr = f"{lit}::{typ}"
        try:
            orig = conn.execute(f"select ({expr})::text").fetchone()[0]
        except psycopg.Error as e:
            continue
        coltype = typ if typ != "record" else None
        if coltype is None:
            continue
        try:
            conn.execute("drop table if exists brt")
            conn.execute(f"create table brt(v {coltype})")
            data = b""
            with conn.cursor().copy(f"copy (select {expr}) to stdout (format binary)") as cp:
                for chunk in cp:
                    data += bytes(chunk)
            with conn.cursor().copy("copy brt from stdin (format binary)") as cp:
                cp.write(data)
            back = conn.execute("select v::text from brt").fetchone()[0]
            if back != orig:
                fails += 1
                print(f"DIFF {expr}: {orig!r} -> {back!r}")
        except psycopg.Error as e:
            fails += 1
            print(f"ERR  {expr}: {orig!r}: {e.sqlstate} {str(e).splitlines()[0]}")
print("fails", fails)
