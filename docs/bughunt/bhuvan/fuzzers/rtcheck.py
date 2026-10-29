"""Text and binary I/O round-trip check over every column in a database.

For each stored value v of type T (sampled from user tables):
  T1: text_in(text_out(v))           -> text_out must reproduce text_out(v)
  B1: recv(send(v))                  -> text_out must equal text_out(v)
  B2: send(recv(send(v)))            -> bytes must equal send(v)
usage: python rtcheck.py PORT DBNAME [per_column_limit]
"""
import sys
from collections import Counter

import psycopg

port, db = int(sys.argv[1]), sys.argv[2]
lim = int(sys.argv[3]) if len(sys.argv) > 3 else 200
conn = psycopg.connect(host="/tmp", port=port, user="postgres", dbname=db, autocommit=True)
pg = conn.pgconn
cur = conn.cursor()
cur.execute("""
SELECT n.nspname, c.relname, a.attname, a.atttypid, format_type(a.atttypid, a.atttypmod),
       t.typsend <> 0 AND t.typreceive <> 0
FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_type t ON t.oid = a.atttypid
WHERE c.relkind IN ('r','m','p') AND a.attnum > 0 AND NOT a.attisdropped
  AND n.nspname NOT IN ('pg_catalog','information_schema','pg_toast')
ORDER BY 1,2,3""")
cols = cur.fetchall()
fails = Counter()
examples = {}
checked = 0
skipped = Counter()


def q(ident):
    return '"' + ident.replace('"', '""') + '"'


for nsp, rel, att, typ, tname, hasbin in cols:
    sql = f"SELECT DISTINCT {q(att)}::text, {q(att)} FROM {q(nsp)}.{q(rel)} WHERE {q(att)} IS NOT NULL LIMIT {lim}"
    try:
        r = pg.exec_params(sql.encode(), [], result_format=1 if hasbin else 0)
    except Exception as e:
        skipped["query"] += 1
        continue
    if r.status != psycopg.pq.ExecStatus.TUPLES_OK:
        skipped["status:" + (r.error_message or b"").decode()[:40]] += 1
        continue
    # column 0 (text cast) arrives in binary as text bytes, fine.
    for i in range(r.ntuples):
        txt = r.get_value(i, 0)
        val = r.get_value(i, 1)
        checked += 1
        # T1
        r1 = pg.exec_params(b"SELECT $1::text", [txt], [typ], [0], result_format=0)
        if r1.status != psycopg.pq.ExecStatus.TUPLES_OK:
            k = ("T1-error", tname, (r1.error_message or b"").decode().splitlines()[0][:60])
        elif r1.get_value(0, 0) != txt:
            k = ("T1-diff", tname)
        else:
            k = None
        if k:
            fails[k] += 1
            examples.setdefault(k, (nsp, rel, att, txt, r1.get_value(0, 0) if r1.ntuples else None))
        if not hasbin:
            continue
        r2 = pg.exec_params(b"SELECT $1::text, $1", [val], [typ], [1], result_format=1)
        if r2.status != psycopg.pq.ExecStatus.TUPLES_OK:
            k = ("B-error", tname, (r2.error_message or b"").decode().splitlines()[0][:60])
            fails[k] += 1
            examples.setdefault(k, (nsp, rel, att, txt, None))
            continue
        if r2.get_value(0, 0) != txt:
            k = ("B1-diff", tname)
            fails[k] += 1
            examples.setdefault(k, (nsp, rel, att, txt, r2.get_value(0, 0)))
        if r2.get_value(0, 1) != val:
            k = ("B2-diff", tname)
            fails[k] += 1
            examples.setdefault(k, (nsp, rel, att, val, r2.get_value(0, 1)))

print(f"columns={len(cols)} values={checked} skipped={dict(skipped)}")
for k, c in fails.most_common():
    print(c, k)
    print("    ", examples[k])
