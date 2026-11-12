import random, sys
from B_h import *

SCHEMA = """
DROP TABLE IF EXISTS t1, t2, t3, t4 CASCADE;
CREATE TABLE t1(a int NOT NULL, b int, c text);
CREATE TABLE t2(a int NOT NULL, b int, c text);
CREATE TABLE t3(a int, b int, c text);
CREATE TABLE t4(a int, b int, c text);
INSERT INTO t1 SELECT i, NULLIF(i%4,0), CASE WHEN i%3=0 THEN NULL ELSE 'v'||(i%3) END FROM generate_series(1,9) i;
INSERT INTO t2 SELECT i%6, NULLIF(i%3,1), CASE WHEN i%2=0 THEN NULL ELSE 'v'||(i%4) END FROM generate_series(2,10) i;
INSERT INTO t3 SELECT NULLIF(i%5,2), i%3, 'v'||(i%2) FROM generate_series(0,7) i;
INSERT INTO t4 VALUES (NULL,NULL,NULL),(1,NULL,'v1'),(NULL,1,NULL),(2,2,'v2'),(0,1,'v0');
CREATE INDEX ON t2(a); CREATE INDEX ON t3(b);
ANALYZE;
"""
TABLES = ['t1', 't2', 't3', 't4']
INTC = ['a', 'b']

class G:
    def __init__(s, rnd):
        s.r = rnd; s.n = 0
    def alias(s):
        s.n += 1; return 'x%d' % s.n
    def iexpr(s, rels, depth=0):
        r = s.r
        a = r.choice(rels)
        k = r.random()
        base = '%s.%s' % (a, r.choice(INTC))
        if depth > 1 or k < 0.55:
            return base
        if k < 0.65: return 'coalesce(%s, %d)' % (base, r.randint(0, 2))
        if k < 0.72: return str(r.randint(0, 3))
        if k < 0.8: return '(%s + %s)' % (base, s.iexpr(rels, depth + 1))
        if k < 0.87: return 'CASE WHEN %s IS NULL THEN %d ELSE %s END' % (base, r.randint(0, 2), base)
        if k < 0.92: return 'nullif(%s, %d)' % (base, r.randint(0, 2))
        return '(%s IS NULL)::int' % base
    def leaf(s, depth, outer):
        r = s.r
        t = r.choice(TABLES)
        a = s.alias()
        k = r.random()
        if depth > 0 and k < 0.2:
            # subquery producing non-strict outputs (become PHVs)
            inner_rels, f = s.from_(depth - 1, [])
            sel = 'coalesce(%s, 0) AS a, %s AS b' % (s.iexpr(inner_rels), s.r.choice(['1', s.iexpr(inner_rels), '%s.b' % inner_rels[0], 'NULL::int']))
            w = ' WHERE ' + s.pred(inner_rels) if r.random() < 0.5 else ''
            return [a], '(SELECT %s FROM %s%s) %s' % (sel, f, w, a)
        if depth > 0 and k < 0.3 and outer:
            o = r.choice(outer)
            inner = s.alias()
            sel = r.choice(['%s.a, %s.b' % (inner, o), '%s.a, coalesce(%s.b, %s.a) AS b' % (inner, o, inner),
                            '%s.a + %s.a AS a, %s.b' % (inner, o, inner)])
            w = r.choice(['%s.a = %s.a' % (inner, o), '%s.b > %s.b' % (inner, o), 'true', '%s.a IS NOT NULL' % o])
            return [a], 'LATERAL (SELECT %s FROM %s %s WHERE %s) %s' % (sel, t, inner, w, a)
        if depth > 0 and k < 0.38:
            t2 = r.choice(TABLES)
            return [a], '(SELECT a, b FROM %s UNION ALL SELECT %s, b FROM %s) %s' % (t, r.choice(['a', 'b + 1', '2', 'NULL::int']), t2, a)
        if depth > 0 and k < 0.45:
            g = r.choice(['a', 'b'])
            return [a], '(SELECT %s AS a, %s AS b FROM %s GROUP BY %s) %s' % (g, r.choice(['count(*)', 'max(a)', 'sum(b)', 'count(b)']), t, g, a)
        if depth > 0 and k < 0.5:
            return [a], '(SELECT DISTINCT a, b FROM %s) %s' % (t, a)
        if depth > 0 and k < 0.55:
            return [a], '(SELECT a, b FROM %s ORDER BY b NULLS FIRST, a LIMIT 100) %s' % (t, a)
        return [a], '%s %s' % (t, a)
    def from_(s, depth, outer):
        r = s.r
        if depth <= 0 or r.random() < 0.3:
            return s.leaf(depth, outer)
        la, l = s.from_(depth - 1, outer)
        ra, rr = s.from_(depth - 1, outer + la)
        if rr.startswith('LATERAL'):
            jt = r.choice(['LEFT JOIN', 'JOIN'])
        else:
            jt = r.choice(['LEFT JOIN', 'LEFT JOIN', 'FULL JOIN', 'JOIN', 'RIGHT JOIN'])
        on = '%s = %s' % (s.iexpr(la), s.iexpr(ra))
        if r.random() < 0.3:
            on += ' AND ' + s.pred(la + ra)
        return la + ra, '(%s %s %s ON %s)' % (l, jt, rr, on)
    def pred(s, rels):
        r = s.r
        k = r.random()
        if k < 0.2: return '%s IS NULL' % s.iexpr(rels)
        if k < 0.35: return '%s IS NOT NULL' % s.iexpr(rels)
        if k < 0.55: return '%s > %d' % (s.iexpr(rels), r.randint(0, 3))
        if k < 0.7: return '%s = %s' % (s.iexpr(rels), s.iexpr(rels))
        if k < 0.78: return 'EXISTS (SELECT 1 FROM %s z WHERE z.a = %s)' % (r.choice(TABLES), s.iexpr(rels))
        if k < 0.84: return '%s NOT IN (SELECT a FROM t1)' % s.iexpr(rels)
        if k < 0.9: return '%s IN (SELECT b FROM %s)' % (s.iexpr(rels), r.choice(TABLES))
        return '%s IS DISTINCT FROM %s' % (s.iexpr(rels), s.iexpr(rels))
    def query(s):
        r = s.r
        rels, f = s.from_(r.randint(1, 3), [])
        w = ''
        if r.random() < 0.8:
            w = ' WHERE ' + r.choice([' AND ', ' OR ']).join(s.pred(rels) for _ in range(r.randint(1, 2)))
        if r.random() < 0.3:
            g = s.iexpr(rels)
            return 'SELECT %s, count(*), sum(%s) FROM %s%s GROUP BY 1' % (g, s.iexpr(rels), f, w)
        sel = ', '.join([s.iexpr(rels) for _ in range(r.randint(1, 4))])
        ob = ''
        if r.random() < 0.3:
            ob = ' ORDER BY %s' % s.iexpr(rels)
        return 'SELECT %s FROM %s%s%s' % (sel, f, w, ob)

VARIANTS = [(), ('enable_hashjoin=off', 'enable_mergejoin=off'), ('enable_nestloop=off', 'enable_hashjoin=off'),
            ('enable_nestloop=off', 'enable_mergejoin=off'), ('enable_seqscan=off',), ('enable_hashagg=off', 'enable_memoize=off'),
            ('enable_material=off', 'enable_bitmapscan=off', 'enable_indexscan=off')]

if __name__ == '__main__':
    seed = int(sys.argv[1]); n = int(sys.argv[2]); db = sys.argv[3] if len(sys.argv) > 3 else 'postgres'
    cm = conn(5433, db); c18 = conn(5435, db)
    for c in (cm, c18):
        setup(c, SCHEMA)
    g = G(random.Random(seed))
    bad = 0; errs = 0
    for i in range(n):
        q = g.query()
        a = run(cm, q); b = run(c18, q)
        if isinstance(a, str): errs += 1
        if a != b and not any(isinstance(z, str) and 'FULL JOIN is only' in z for z in (a, b)):
            bad += 1
            print('DIFF18', i, q); print('  master', str(a)[:300]); print('  18    ', str(b)[:300])
        elif not isinstance(a, str) and i % 3 == 0:
            v = g.r.choice(VARIANTS[1:])
            x = run(cm, q, v)
            if x != a:
                bad += 1
                print('DIFFSET', v, i, q); print('  base', str(a)[:300]); print('  set ', str(x)[:300])
        if bad > 30: break
        if i % 2000 == 0: print('progress', i, 'bad', bad, 'errs', errs, flush=True)
    print('done', n, 'bad', bad, 'errs', errs)
