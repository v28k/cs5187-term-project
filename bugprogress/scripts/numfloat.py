import itertools, math, sys, psycopg

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5433
conn = psycopg.connect(f"host=localhost port={port} user=postgres dbname=postgres", autocommit=True)

vals = ["'NaN'", "'Infinity'", "'-Infinity'", "0", "1", "-1", "2", "0.5", "-0.5", "10", "1e-20", "1e20", "3"]
un = ["ln({})", "log({})", "log10({})", "exp({})", "sqrt({})", "abs({})", "ceil({})", "floor({})",
      "round({})", "trunc({})", "sign({})", "-{}", "{}::int8", "{}::int4"]
bi = ["log({},{})", "power({},{})", "{}^{}", "mod({},{})", "{}/{}", "{}%{}", "{}*{}", "{}+{}", "{}-{}",
      "div({},{})", "atan2({},{})", "greatest({},{})", "least({},{})"]

def run(e):
    try:
        cur = conn.execute("select (" + e + ")::text")
        return cur.fetchone()[0]
    except psycopg.Error as ex:
        return "ERR:" + (ex.sqlstate or "")

def norm(s):
    if s is None: return None
    if s.startswith("ERR"): return s
    try:
        f = float(s)
    except ValueError:
        return s
    if math.isnan(f) or math.isinf(f): return repr(f)
    return f

diffs = 0
cases = [(u, (v,)) for u in un for v in vals] + [(b, p) for b in bi for p in itertools.product(vals, vals)]
for tmpl, args in cases:
    en = tmpl.format(*[f"{a}::numeric" for a in args])
    ef = tmpl.format(*[f"{a}::float8" for a in args])
    rn, rf = run(en), run(ef)
    nn, nf = norm(rn), norm(rf)
    if nn == nf: continue
    if isinstance(nn, float) and isinstance(nf, float):
        if nf == 0 and abs(nn) < 1e-12: continue
        if nf != 0 and abs(nn - nf) / abs(nf) < 1e-9: continue
    if isinstance(nn, str) and isinstance(nf, str) and nn.startswith("ERR") and nf.startswith("ERR"): continue
    diffs += 1
    print(f"{tmpl:16} {args!s:30} numeric={rn!s:25} float8={rf}")
print("diffs", diffs, "of", len(cases))
