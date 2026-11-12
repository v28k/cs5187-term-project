import sys, random, psycopg

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5433
conn = psycopg.connect(f"host=localhost port={port} user=postgres dbname=postgres", autocommit=True)
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
N = 40

def pick(xs, pnull=0.15):
    return None if random.random() < pnull else random.choice(xs)

conn.execute("drop table if exists wt")
conn.execute("""create table wt(i int primary key, n numeric, f float8, iv interval, b bool,
  s text, j jsonb, r int4range, ts timestamptz, k int, a int[], x bit(4))""")
nums = ["NaN", "Infinity", "-Infinity", "0", "1.5", "-2", "1e10", "0.000001", "3"]
flts = nums + ["-0"]
ivs = ["infinity", "-infinity", "1 day", "-2 hours", "1 mon", "0"]
for i in range(1, N + 1):
    conn.execute("insert into wt values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (
        i, pick(nums), pick(flts), pick(ivs), pick([True, False]), pick(["a", "b", "", "ccc"]),
        pick(['{"a":1}', '{"a":null}', '{"b":2}', '1', 'null', '[1]']),
        pick(["[1,3)", "[2,5)", "empty", "(,)", "[10,11)"]),
        pick(["2020-01-01", "infinity", "-infinity", "1999-12-31 23:00"]),
        pick([1, 2, 3, None]), pick(["{1,2}", "{}", "{NULL}"]), pick(["1010", "0110", "1111"])))

aggs = ["sum(n)", "avg(n)", "count(n)", "min(n)", "max(n)", "stddev(n)", "variance(n)", "var_pop(n)",
        "stddev_pop(n)", "sum(f)", "avg(f)", "min(f)", "max(f)", "sum(iv)", "avg(iv)", "min(iv)", "max(iv)",
        "bool_and(b)", "bool_or(b)", "every(b)", "count(*)", "string_agg(s, ',')", "array_agg(n)",
        "json_agg(j)", "jsonb_agg(j)", "json_agg_strict(j)", "jsonb_agg_strict(j)",
        "jsonb_object_agg(coalesce(s,'z'), j)", "jsonb_object_agg_strict(coalesce(s,'z'), j)",
        "json_object_agg(coalesce(s,'z'), j)", "jsonb_object_agg_unique_strict(i::text, j)",
        "json_objectagg(coalesce(s,'z') : j)", "json_arrayagg(j)", "json_arrayagg(j null on null)",
        "range_agg(r)", "range_intersect_agg(r)", "min(ts)", "max(ts)", "sum(k)", "avg(k)", "sum(k::int8)",
        "avg(k::int8)", "sum(k::int2)", "bit_and(k)", "bit_or(k)", "bit_xor(k)", "bit_and(x)", "bit_xor(x)",
        "array_agg(a)", "count(distinct k)" , "any_value(k)", "stddev(k)", "var_samp(k::int8)",
        "regr_sxx(f, n::float8)", "corr(f, k)", "covar_pop(k, f)", "regr_avgx(k, f)", "sum(n) filter (where b)",
        "avg(iv) filter (where k > 1)", "max(s)", "min(s collate \"C\")", "string_agg(s, j::text)",
        "xmlagg(xmlelement(name e, s))", "array_agg(distinct k)"]
frames = [("rows between 2 preceding and current row", "w.i between t.i-2 and t.i"),
          ("rows between 1 preceding and 2 following", "w.i between t.i-1 and t.i+2"),
          ("rows between unbounded preceding and current row", "w.i <= t.i"),
          ("rows between current row and unbounded following", "w.i >= t.i"),
          ("rows between 3 preceding and 1 preceding", "w.i between t.i-3 and t.i-1"),
          ("rows between 2 preceding and 2 following exclude current row", "w.i between t.i-2 and t.i+2 and w.i <> t.i"),
          ("range between 2 preceding and 1 following", "w.i between t.i-2 and t.i+1"),
          ("groups between 1 preceding and current row", "w.i between t.i-1 and t.i")]
bad = 0
for ag in aggs:
    for fr, cond in frames:
        if "distinct" in ag:
            continue
        sub_ag = ag
        # ordered aggregates: give subquery the same input order as the window frame
        if ag.endswith(")") and "filter" not in ag and any(x in ag for x in ("agg", "objectagg", "arrayagg")):
            sub_ag = ag[:-1] + " order by w.i)"
            if "json_objectagg" in ag or "json_arrayagg" in ag:
                sub_ag = ag[:-1].replace(" null on null", "") + " order by w.i" + (" null on null)" if "null on null" in ag else ")")
                if "json_arrayagg(j" in ag:
                    sub_ag = "json_arrayagg(w.j order by w.i" + (" null on null)" if "null on null" in ag else ")")
        wexpr = ag
        sexpr = sub_ag
        for c in ["n", "f", "iv", "b", "s", "j", "r", "ts", "k", "a", "x", "i"]:
            pass
        q1 = f"select i, ({wexpr} over (order by i {fr}))::text from wt order by i"
        q2 = (f"select i, (select ({sexpr})::text from wt w where {cond}) from wt t order by i")
        # qualify columns in the subquery with w.
        import re
        q2 = q2.replace(f"({sexpr})", "(" + re.sub(r"(?<![\w.'\"])(n|f|iv|b|s|j|r|ts|k|a|x|i)(?![\w'\"(])", r"w.\1", sexpr) + ")")
        try:
            r1 = conn.execute(q1).fetchall()
        except psycopg.Error as e:
            r1 = "ERR " + str(e.sqlstate) + " " + str(e).splitlines()[0]
        try:
            r2 = conn.execute(q2).fetchall()
        except psycopg.Error as e:
            r2 = "ERR " + str(e.sqlstate) + " " + str(e).splitlines()[0]
        if r1 != r2:
            bad += 1
            print("MISMATCH", ag, "|", fr)
            if isinstance(r1, str) or isinstance(r2, str):
                print("  ", r1 if isinstance(r1, str) else "ok", "||", r2 if isinstance(r2, str) else "ok")
            else:
                for a, b in zip(r1, r2):
                    if a != b:
                        print("   i=%s win=%s sub=%s" % (a[0], a[1], b[1]))
                        break
print("mismatches", bad)
