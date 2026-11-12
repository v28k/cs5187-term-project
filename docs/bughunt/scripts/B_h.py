import psycopg, sys, collections

def conn(port=5433, db='postgres'):
    c = psycopg.connect(host='/tmp', port=port, user='postgres', dbname=db, autocommit=True)
    return c

def run(c, sql, settings=()):
    with c.cursor() as cur:
        cur.execute("RESET ALL")
        for s in settings:
            cur.execute("SET " + s)
        try:
            cur.execute(sql)
            rows = cur.fetchall() if cur.description else []
            return sorted(collections.Counter(map(repr, rows)).items())
        except Exception as e:
            return 'ERR ' + type(e).__name__ + ': ' + str(e).splitlines()[0]

def explain(c, sql, settings=()):
    with c.cursor() as cur:
        cur.execute("RESET ALL")
        for s in settings:
            cur.execute("SET " + s)
        cur.execute("EXPLAIN (COSTS OFF) " + sql)
        return "\n".join(r[0] for r in cur.fetchall())

def compare(c, sql, variants, label=''):
    base = run(c, sql, variants[0])
    bad = []
    for v in variants[1:]:
        r = run(c, sql, v)
        if r != base:
            bad.append((v, r))
    if bad:
        print("MISMATCH", label, sql)
        print("  base", variants[0], str(base)[:300])
        for v, r in bad:
            print("  ", v, str(r)[:300])
    return not bad

def setup(c, script):
    with c.cursor() as cur:
        cur.execute(script)
