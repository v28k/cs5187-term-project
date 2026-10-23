import sys, random, itertools, psycopg
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5433
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
random.seed(seed)
def connect():
    return psycopg.connect(f"host=localhost port={port} user=postgres dbname=postgres", autocommit=True)
conn = connect()
conn.execute("""
drop schema if exists xs cascade; create schema xs; set search_path=xs;
create domain dbool as bool; create domain dint as int; create domain dtext as text collate "C";
create domain dnum as numeric(10,2); create domain ddbool as dbool; create domain darr as int[];
create domain dint_ck as int check (value > -100);
create table t(a int, b dbool, c dint, d dtext, e dnum, f ddbool, g darr, h bool, i text, k dint_ck, r int4range, j jsonb);
create table pt(a int, b dbool, c dint, d dtext, e dnum, f ddbool, g darr, h bool, i text, k dint_ck, r int4range, j jsonb) partition by list (a);
create table pt0 partition of pt for values in (0,1,2,3); create table pt1 partition of pt default;
create table ip(a int, b dbool, c dint, d dtext, e dnum, f ddbool, g darr, h bool, i text, k dint_ck, r int4range, j jsonb);
create table ic() inherits (ip);
insert into t select x % 7, (x % 3 = 0), x % 5, (x % 4)::text, (x % 6) / 2.0, (x % 2 = 0), array[x % 3, x % 2],
  (x % 5 = 0), (x % 9)::text, x % 11, int4range(x % 4, x % 4 + 2), jsonb_build_object('a', x % 3)
  from generate_series(1, 3000) x;
insert into pt select * from t; insert into ip select * from t where a < 3; insert into ic select * from t where a >= 3;
update t set b = null where a = 1; update t set c = null where a = 2; update t set d = null where a = 3;
""")
cols = ["a", "b", "c", "d", "e", "f", "h", "i", "k"]
exprs = ["(a + c)", "(b::bool)", "(not b)", "(d || i)", "(e * 2)", "(c::int)", "(lower(d))", "(b and h)", "(g[1])",
         "(upper(r))", "(j->>'a')", "(c is null)", "(b is true)", "(coalesce(b, f))", "(a = c)", "(abs(c))"]
stats = []
for n in range(10):
    k = random.randint(2, 4)
    items = random.sample(cols + exprs, k)
    kinds = random.choice(["", "(mcv)", "(ndistinct)", "(dependencies)", "(mcv, dependencies)", "(ndistinct, mcv)"])
    tab = random.choice(["t", "pt", "ip", "ic", "pt0"])
    stats.append(f"create statistics s{n} {kinds} on {', '.join(items)} from {tab}")
ok = 0
for s in stats:
    try:
        conn.execute("set search_path=xs"); conn.execute(s); ok += 1
    except psycopg.Error as e:
        pass
conn.execute("set search_path=xs; analyze t; analyze pt; analyze ip; analyze ic")
atoms = ["a = 1", "a < 3", "a in (1,2)", "a = any(array[1,2])", "b", "not b", "b = true", "b <> false", "b is true",
         "b is not false", "b is null", "b is not null", "c = 1", "c = 1::dint", "c in (1, 2)", "c = any('{1,2}'::int[])",
         "c < 3", "c between 1 and 3", "d = '1'", "d < '2'", "d like '1%'", "d in ('1','2')", "d = any(array['1'::dtext])",
         "e = 1.5", "e > 1", "f", "not f", "f = b", "h", "h and b", "i = '3'", "k = 2", "k < 4", "(a + c) = 3",
         "(b::bool)", "(not b)", "(d || i) = '11'", "(e * 2) = 3", "(c::int) = 2", "lower(d) = '1'", "(b and h)",
         "g[1] = 1", "g = '{1,1}'", "upper(r) = 2", "(j->>'a') = '1'", "(c is null)", "(b is true)",
         "coalesce(b, f)", "(a = c)", "abs(c) = 1", "row(a, c) = row(1, 1)", "row(a, c) < row(2, 2)",
         "b is distinct from true", "c is not distinct from 1", "b = (select true)", "a = c", "b = h", "b in (true)",
         "b = any(array[true])", "c = 1 or b", "not (c = 1 and b)", "f is unknown", "b::int = 1", "(c::int8) = 1",
         "(b + 1) is null", "d = '1' collate \"C\"", "d > all(array['1','2'])", "c <> all('{1,2}')", "(a + c) in (1, 2)",
         "(a + c) = any(array[1, null])", "abs(c) in (1, 2)", "lower(d) in ('1', '2')", "(d || i) like '1%'", "g && '{1}'",
         "r @> 2", "j @> '{\"a\":1}'", "(j->>'a') in ('1','2')", "(b is true) = (h is true)", "b is not distinct from h",
         "(a + c) is not distinct from 3", "e is distinct from 1.5", "row(a, b) is null", "(a, c) in ((1,1),(2,2))",
         "a = 1 and a = 1", "(a + c) = 2 and (a + c) in (2, 3)", "lower(d) = '1' and lower(d) in ('1')", "(b is true) and (b is true)",
         "(not b) and (not b)", "coalesce(b, f) and coalesce(b, f)", "(abs(c)) = 1 and abs(c) < 3",
         "case when b then a else c end = 1", "nullif(a, c) = 1", "greatest(a, c) = 3", "(c::text) = '1'", "(a::numeric) = 1"]
bad = 0
seen = set()
for trial in range(4000):
    n = random.randint(1, 4)
    parts = random.sample(atoms, n)
    op = random.choice([" and ", " or ", " and ", " and not "])
    where = op.join(f"({p})" for p in parts)
    q = random.choice([
        f"explain select * from t where {where}",
        f"explain select * from {random.choice(['pt','ip','ic','pt0'])} where {where}",
        f"explain select count(*) from {random.choice(['pt','ip'])} where {where} group by {', '.join(random.sample(cols + exprs, random.randint(1, 3)))}",
        f"explain select * from t t1 left join pt t2 on t1.a = t2.a and t1.b = t2.b and t1.c = t2.c where {where.replace('(a', '(t1.a')}",
        f"explain select count(*) from t where {where} group by {', '.join(random.sample(cols + exprs, random.randint(1, 3)))}",
        f"explain select 1 from t group by rollup({', '.join(random.sample(cols + exprs, 2))}), {random.choice(cols + exprs)}",
        f"explain select 1 from t group by grouping sets (({random.choice(cols + exprs)}), ({', '.join(random.sample(cols + exprs, 2))}))",
        f"explain select distinct {', '.join(random.sample(cols + exprs, random.randint(1, 3)))} from t where {where}",
        f"explain select * from t t1 join t t2 on t1.a = t2.a and t1.c = t2.c where {where.replace('(a', '(t1.a')}",
    ])
    try:
        conn.execute("set search_path=xs")
        conn.execute(q)
    except psycopg.Error as e:
        st = e.sqlstate or ""
        msg = str(e).splitlines()[0]
        if st.startswith("XX") or st == "" or "server closed" in msg or "terminat" in msg:
            if "corrupt MVNDistinct" in msg or "expression not found in statistics" in msg:
                continue
            key = msg
            if key not in seen:
                seen.add(key)
                print(st, "|", msg, "|", q)
            bad += 1
            if conn.closed or st == "":
                conn = connect()
print("stats ok", ok, "bad", bad)
for s in stats: print("--", s)
