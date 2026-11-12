import sys, psycopg
port=int(sys.argv[1])
conn=psycopg.connect(f"host=localhost port={port} user=postgres dbname=postgres", autocommit=True)
lits=['<?xml version="1.0"?><a/>','<?xml version="1.0" encoding="UTF-8"?><a/>','<?xml version="1.0" standalone="yes"?><a/>',
 '<?xml version="1.0"?>text','<?xml version="1.0"?>','<?xml version="1.1"?><a/>','<?xml version="1.0"?><!DOCTYPE a><a/>',
 '<!DOCTYPE a><a/>','  <?xml version="1.0"?><a/>','<?xml version="1.0"?>\n<a/>\n<b/>','<?xml version="1.0"?><!-- c --><a/>', '<?pi x?><a/>']
for opt in ['content','document']:
  conn.execute(f"set xmloption={opt}")
  for l in lits:
    try:
      orig=conn.execute("select %s::xml::text",(l,)).fetchone()[0]
    except psycopg.Error as e:
      print(opt, repr(l), "text-in ERR", str(e).splitlines()[0]); continue
    conn.execute("drop table if exists x; create table x(v xml)")
    data=b""
    with conn.cursor().copy("copy (select %s::xml) to stdout (format binary)" % conn.execute("select quote_literal(%s)",(l,)).fetchone()[0]) as cp:
      for c in cp: data+=bytes(c)
    try:
      with conn.cursor().copy("copy x from stdin (format binary)") as cp: cp.write(data)
      back=conn.execute("select v::text from x").fetchone()[0]
    except psycopg.Error as e:
      back="ERR "+str(e).splitlines()[0]
    print(opt, repr(l), "->", repr(orig), "| bin:", repr(back), "" if orig==back else "   <<<DIFF")
