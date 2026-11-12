import random, sys
from B_h import *

SCHEMA = """
DROP TABLE IF EXISTS t1, t2, t3, t4 CASCADE;
DROP TYPE IF EXISTS pr CASCADE;
CREATE TYPE pr AS (x int, y int);
CREATE TABLE t1(id int NOT NULL, a int, b int NOT NULL, p pr);
CREATE TABLE t2(id int NOT NULL, a int, b int NOT NULL, p pr);
CREATE TABLE t3(id int, a int, b int, p pr NOT NULL);
CREATE TABLE t4(a int, b int);
INSERT INTO t1 SELECT i, CASE WHEN i%4=0 THEN NULL ELSE i%5 END, i%3,
  CASE WHEN i%5=0 THEN NULL WHEN i%5=1 THEN ROW(NULL,NULL)::pr ELSE ROW(i%3, NULLIF(i%4,0))::pr END FROM generate_series(1,12) i;
INSERT INTO t2 SELECT i, CASE WHEN i%3=0 THEN NULL ELSE i%4 END, i%2,
  CASE WHEN i%4=0 THEN NULL WHEN i%4=1 THEN ROW(NULL,NULL)::pr ELSE ROW(i%2, i%3)::pr END FROM generate_series(3,14) i;
INSERT INTO t3 SELECT CASE WHEN i%5=0 THEN NULL ELSE i END, CASE WHEN i%2=0 THEN NULL ELSE i%3 END, i%4,
  CASE WHEN i%3=0 THEN ROW(NULL,NULL)::pr ELSE ROW(i%2, NULL)::pr END FROM generate_series(2,10) i;
INSERT INTO t4 VALUES (NULL,NULL),(1,NULL),(NULL,1),(2,2),(0,1);
ANALYZE;
"""
TABLES = ['t1', 't2', 't3', 't4']
COLS = {'t1': ['id', 'a', 'b', 'p'], 't2': ['id', 'a', 'b', 'p'], 't3': ['id', 'a', 'b', 'p'], 't4': ['a', 'b']}
INTC = {t: [c for c in COLS[t] if c != 'p'] for t in TABLES}

class G:
    def __init__(s, rnd):
        s.r = rnd
        s.n = 0
    def alias(s):
        s.n += 1
        return 'x%d' % s.n
    def rel(s, depth):
        """returns (sql, list of (alias, table))"""
        r = s.r
        if depth <= 0 or r.random() < 0.35:
            t = r.choice(TABLES)
            a = s.alias()
            k = r.random()
            if k < 0.15:
                # subquery with strict qual inside
                c = r.choice(INTC[t])
                q = r.choice(['%s > 0' % c, '%s IS NOT NULL' % c, '%s = %s' % (c, c), 'p IS NOT NULL' if 'p' in COLS[t] else 'true',
                              '(p).x IS NOT NULL' if 'p' in COLS[t] else 'true'])
                return '(SELECT * FROM %s WHERE %s) %s' % (t, q, a), [(a, t)]
            if k < 0.22:
                c = r.choice(INTC[t])
                return '(SELECT * FROM %s WHERE %s IS NOT NULL OFFSET 0) %s' % (t, c, a), [(a, t)]
            return '%s %s' % (t, a), [(a, t)]
        l, la = s.rel(depth - 1)
        rr, ra = s.rel(depth - 1)
        jt = r.choice(['LEFT JOIN', 'LEFT JOIN', 'FULL JOIN', 'JOIN', 'RIGHT JOIN', 'FULL JOIN'])
        on = s.onq(la, ra)
        return '(%s %s %s ON %s)' % (l, jt, rr, on), la + ra
    def col(s, rels, intonly=True):
        a, t = s.r.choice(rels)
        cs = INTC[t] if intonly else COLS[t]
        return '%s.%s' % (a, s.r.choice(cs))
    def onq(s, la, ra):
        r = s.r
        parts = ['%s = %s' % (s.col(la), s.col(ra))]
        if r.random() < 0.4:
            parts.append(s.pred(ra + la, simple=True))
        return ' AND '.join(parts)
    def pred(s, rels, simple=False):
        r = s.r
        k = r.random()
        a, t = r.choice(rels)
        if k < 0.25:
            return '%s IS NULL' % s.col(rels)
        if k < 0.35:
            return '%s IS NULL' % a
        if k < 0.42:
            return '%s IS NOT NULL' % a
        if k < 0.5 and 'p' in COLS[t]:
            return '%s.p IS %sNULL' % (a, r.choice(['', 'NOT ']))
        if k < 0.6:
            return '%s IS NOT NULL' % s.col(rels)
        if k < 0.7:
            return '%s > %d' % (s.col(rels), r.randint(0, 3))
        if k < 0.78:
            return 'NOT (%s IS NULL)' % a
        if k < 0.85 and not simple:
            t2 = r.choice(TABLES)
            c2 = r.choice(INTC[t2])
            w = r.choice(['', ' WHERE %s IS NOT NULL' % c2])
            return '%s NOT IN (SELECT %s FROM %s%s)' % (s.col(rels), c2, t2, w)
        if k < 0.9:
            return 'ROW(%s, %s) IS NULL' % (s.col(rels), s.col(rels))
        if k < 0.95:
            return 'coalesce(%s, %s) IS NULL' % (s.col(rels), s.col(rels))
        return '%s IS DISTINCT FROM %s' % (s.col(rels), s.col(rels))
    def query(s):
        r = s.r
        f, rels = s.rel(r.randint(1, 3))
        w = [s.pred(rels) for _ in range(r.randint(1, 3))]
        conj = r.choice([' AND ', ' AND ', ' OR '])
        sel = ', '.join('%s.%s' % (a, c) for a, t in rels for c in COLS[t])
        return 'SELECT %s FROM %s WHERE %s' % (sel, f, conj.join(w))

if __name__ == '__main__':
    seed = int(sys.argv[1]); n = int(sys.argv[2])
    cm = conn(5433); c18 = conn(5435)
    for c in (cm, c18):
        setup(c, SCHEMA)
    g = G(random.Random(seed))
    bad = 0
    for i in range(n):
        q = g.query()
        a = run(cm, q); b = run(c18, q)
        if a != b:
            if isinstance(a, str) and isinstance(b, str):
                continue
            bad += 1
            print('DIFF', i, q)
            print('  master', str(a)[:400])
            print('  18    ', str(b)[:400])
            if bad > 5: break
    print('done', n, 'bad', bad)
