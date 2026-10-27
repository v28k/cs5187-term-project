"""Differential fuzzer for JSON_TABLE NESTED PATH + PLAN clauses.

Oracle: every JSON_TABLE is translated into an equivalent query built only
from jsonb_path_query() (row patterns), JSON_VALUE()/JSON_EXISTS() (columns),
WITH ORDINALITY, LEFT JOIN LATERAL / JOIN LATERAL (parent/child OUTER/INNER),
UNION ALL with NULL padding (sibling UNION) and CROSS JOIN (sibling CROSS).
Both are evaluated by the same server; results are compared as multisets.

usage: jtfuzz.py PORT SEED N [--verbose]
"""
import json, random, sys, os, itertools
import psycopg

INT_KEYS = ["v", "w"]
CHILD_KEYS = ["a", "b", "c", "d"]


class Node:
    def __init__(self, name, path, key):
        self.name = name
        self.path = path      # jsonpath text, e.g. '$.a[*]'
        self.key = key        # child key used in data (None for '$' paths)
        self.cols = []        # (colname, kind, sqltype, keypath)
        self.children = []
        self.pc = "OUTER"     # parent/child join for this node's children
        self.sib = None       # sibling plan tree over children


class Gen:
    def __init__(self, rng):
        self.rng = rng
        self.ncol = 0
        self.npath = 0

    def colname(self):
        self.ncol += 1
        return f"c{self.ncol}"

    def pathname(self):
        self.npath += 1
        return f"p{self.npath}"

    def node(self, depth, root=False):
        r = self.rng
        if root:
            path = r.choice(["$[*]", "$[*]", "$", "$.items[*]"])
            key = None
        else:
            key = r.choice(CHILD_KEYS)
            path = r.choice([f"$.{key}[*]", f"$.{key}[*]", f"$.{key}", f"$.{key}[*] ? (@.v != 3)", f"$.{key}[last]"])
        n = Node(self.pathname(), path, key)
        if r.random() < 0.5:
            n.cols.append((self.colname(), "ord", "int", None))
        for _ in range(r.randint(0, 2)):
            k = r.choice(INT_KEYS)
            kind = r.choice(["int", "int", "int", "exists", "text", "jsonb"])
            if kind == "exists":
                n.cols.append((self.colname(), "exists", "bool", f"$.{k}"))
            elif kind == "text":
                n.cols.append((self.colname(), "text", "text", f"$.{k}"))
            elif kind == "jsonb":
                n.cols.append((self.colname(), "jsonb", "jsonb", f"$.{k}"))
            else:
                n.cols.append((self.colname(), "int", "int", f"$.{k}"))
        if depth < 3:
            nch = r.choice([0, 1, 1, 2, 2, 3]) if depth < 2 else r.choice([0, 0, 1, 2])
            used = set()
            for _ in range(nch):
                c = self.node(depth + 1)
                n.children.append(c)
        if not n.cols and not n.children:
            n.cols.append((self.colname(), "int", "int", "$.v"))
        return n

    def random_plan(self, n):
        """assign pc/sib randomly for explicit PLAN"""
        r = self.rng
        n.pc = r.choice(["OUTER", "INNER"])
        if n.children:
            n.sib = self.sibtree([("leaf", c) for c in r.sample(n.children, len(n.children))])
        for c in n.children:
            self.random_plan(c)

    def sibtree(self, items):
        r = self.rng
        while len(items) > 1:
            i = r.randrange(len(items) - 1)
            op = r.choice(["UNION", "CROSS"])
            items[i:i + 2] = [(op, items[i], items[i + 1])]
        return items[0]

    def uniform_plan(self, n, pc, sib):
        n.pc = pc
        if n.children:
            t = ("leaf", n.children[0])
            for c in n.children[1:]:
                t = (sib, t, ("leaf", c))
            n.sib = t
        for c in n.children:
            self.uniform_plan(c, pc, sib)

    # ---- data ----
    def item(self, node, depth):
        r = self.rng
        o = {}
        for k in INT_KEYS:
            x = r.random()
            if x < 0.55:
                o[k] = r.randint(1, 4)
            elif x < 0.65:
                o[k] = None
            elif x < 0.72:
                o[k] = str(r.randint(1, 4))
            elif x < 0.76:
                o[k] = [r.randint(1, 4)]
            elif x < 0.79:
                o[k] = {"z": 1}
            # else missing
        for c in node.children:
            if c.key:
                o[c.key] = self.childval(c, depth + 1)
        return o

    def childval(self, node, depth):
        r = self.rng
        x = r.random()
        if x < 0.6:
            return [self.item(node, depth) for _ in range(r.randint(0, 3))]
        if x < 0.7:
            return self.item(node, depth)      # lax: non-array unwrapped
        if x < 0.78:
            return None                        # JSON null item
        if x < 0.84:
            return r.randint(1, 4)             # scalar item
        if x < 0.9:
            return []
        return [self.item(node, depth), None, 7]

    def doc(self, root):
        r = self.rng
        if root.path == "$.items[*]":
            return {"items": [self.item(root, 0) for _ in range(r.randint(0, 3))]}
        if root.path == "$":
            return self.item(root, 0)
        x = r.random()
        if x < 0.85:
            return [self.item(root, 0) for _ in range(r.randint(0, 3))]
        return self.item(root, 0)


def colspec(c):
    name, kind, typ, kp = c
    if kind == "ord":
        return f"{name} FOR ORDINALITY"
    if kind == "exists":
        return f"{name} bool EXISTS PATH '{kp}'"
    return f"{name} {typ} PATH '{kp}'"


def jt_columns(n, top=False):
    parts = [colspec(c) for c in n.cols]
    for ch in n.children:
        parts.append(f"NESTED PATH '{ch.path}' AS {ch.name} COLUMNS ({jt_columns(ch)})")
    return ", ".join(parts)


def plan_text_node(n):
    """plan for node n including its children: 'n' or 'n OUTER <primary>'"""
    if not n.children:
        return n.name
    return f"{n.name} {n.pc} {plan_text_primary(n.sib)}"


def plan_text_primary(t):
    if t[0] == "leaf":
        c = t[1]
        s = plan_text_node(c)
        return s if not c.children else f"({s})"
    return f"({plan_text_sib(t)})"


def plan_text_sib(t):
    if t[0] == "leaf":
        return plan_text_primary(t)
    op, l, r = t
    return f"{plan_text_primary(l)} {op} {plan_text_primary(r)}"


def allcols(n):
    out = list(n.cols)
    for ch in n.children:
        out += allcols(ch)
    return out


class Ref:
    def __init__(self):
        self.k = 0

    def alias(self):
        self.k += 1
        return f"r{self.k}"

    def colexpr(self, c, v):
        name, kind, typ, kp = c
        if kind == "ord":
            return f"{v}.ord::int"
        if kind == "exists":
            return f"JSON_EXISTS({v}.val, '{kp}')"
        if kind == "jsonb":
            return f"JSON_QUERY({v}.val, '{kp}')"
        return f"JSON_VALUE({v}.val, '{kp}' RETURNING {typ})"

    def node_sql(self, n, ctx):
        v = self.alias()
        src = f"jsonb_path_query({ctx}, '{n.path}') WITH ORDINALITY AS {v}(val, ord)"
        own = [f"{self.colexpr(c, v)} AS {c[0]}" for c in n.cols]
        if not n.children:
            return f"SELECT {', '.join(own) if own else '1 AS dummy_' + v} FROM {src}", [c for c in n.cols]
        s = self.alias()
        csql, ccols = self.sib_sql(n.sib, f"{v}.val")
        jt = "LEFT JOIN LATERAL" if n.pc == "OUTER" else "JOIN LATERAL"
        sel = own + [f"{s}.{c[0]}" for c in ccols]
        return f"SELECT {', '.join(sel)} FROM {src} {jt} ({csql}) {s} ON true", n.cols + ccols

    def sib_sql(self, t, ctx):
        if t[0] == "leaf":
            return self.node_sql(t[1], ctx)
        op, l, r = t
        lsql, lcols = self.sib_sql(l, ctx)
        rsql, rcols = self.sib_sql(r, ctx)
        a, b = self.alias(), self.alias()
        if op == "CROSS":
            sel = [f"{a}.{c[0]}" for c in lcols] + [f"{b}.{c[0]}" for c in rcols]
            return f"SELECT {', '.join(sel)} FROM ({lsql}) {a} CROSS JOIN ({rsql}) {b}", lcols + rcols
        sel1 = [f"{a}.{c[0]}" for c in lcols] + [f"NULL::{c[2]} AS {c[0]}" for c in rcols]
        sel2 = [f"NULL::{c[2]} AS {c[0]}" for c in lcols] + [f"{b}.{c[0]}" for c in rcols]
        return (f"SELECT {', '.join(sel1)} FROM ({lsql}) {a} UNION ALL "
                f"SELECT {', '.join(sel2)} FROM ({rsql}) {b}"), lcols + rcols


def build(gen, root, mode):
    if mode == "explicit":
        gen.random_plan(root)
        plan = f" PLAN ({plan_text_node(root)})" if root.children else ""
    elif mode == "default":
        pc = gen.rng.choice(["OUTER", "INNER"])
        sib = gen.rng.choice(["UNION", "CROSS"])
        gen.uniform_plan(root, pc, sib)
        form = gen.rng.choice([f"{pc}, {sib}", f"{sib}, {pc}", pc, sib])
        if form == pc:
            gen.uniform_plan(root, pc, "UNION")
        elif form == sib:
            gen.uniform_plan(root, "OUTER", sib)
        plan = f" PLAN DEFAULT ({form})"
    else:
        gen.uniform_plan(root, "OUTER", "UNION")
        plan = ""
    cols = allcols(root)
    names = ", ".join(f"jt.{c[0]}" for c in cols)
    jtq = (f"SELECT d.id, {names} FROM jtdocs d, JSON_TABLE(d.js, '{root.path}' AS {root.name} "
           f"COLUMNS ({jt_columns(root)}){plan}) jt")
    ref = Ref()
    rsql, rcols = ref.node_sql(root, "d.js")
    assert sorted(c[0] for c in rcols) == sorted(c[0] for c in cols)
    names2 = ", ".join(f"q.{c[0]}" for c in cols)
    refq = f"SELECT d.id, {names2} FROM jtdocs d CROSS JOIN LATERAL ({rsql}) q"
    return jtq, refq


def norm(rows):
    return sorted(tuple("<N>" if x is None else (json.dumps(x, sort_keys=True) if isinstance(x, (dict, list)) else str(x)) for x in r) for r in rows)


def main():
    port, seed, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    verbose = "--verbose" in sys.argv
    outdir = os.path.expanduser(f"~/audit/fuzz/out-jt")
    os.makedirs(outdir, exist_ok=True)
    conn = psycopg.connect(f"host=/tmp port={port} user=postgres dbname=postgres", autocommit=True)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '10s'")
    stats = {"ok": 0, "mismatch": 0, "jt_error": 0, "ref_error": 0, "both_error": 0}
    for i in range(n):
        rng = random.Random(seed * 1000003 + i)
        gen = Gen(rng)
        root = gen.node(0, root=True)
        docs = [json.dumps(gen.doc(root)) for _ in range(rng.randint(1, 3))]
        mode = rng.choice(["explicit", "explicit", "default", "none"])
        jtq, refq = build(gen, root, mode)
        setup = ("DROP TABLE IF EXISTS jtdocs; CREATE TEMP TABLE jtdocs(id int, js jsonb); "
                 + " ".join(f"INSERT INTO jtdocs VALUES ({k}, $${d}$$);" for k, d in enumerate(docs)))
        cur.execute(setup)
        res = {}
        for tag, q in (("jt", jtq), ("ref", refq)):
            try:
                cur.execute(q)
                res[tag] = ("ok", norm(cur.fetchall()))
            except psycopg.Error as e:
                res[tag] = ("err", f"{e.sqlstate}: {str(e).splitlines()[0]}")
                if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                    conn.rollback()
        a, b = res["jt"], res["ref"]
        if a[0] == "ok" and b[0] == "ok":
            if a[1] == b[1]:
                stats["ok"] += 1
                continue
            kind = "mismatch"
        elif a[0] == "err" and b[0] == "err":
            stats["both_error"] += 1
            if verbose:
                print("both err", a[1], b[1])
            continue
        else:
            kind = "jt_error" if a[0] == "err" else "ref_error"
        stats[kind] += 1
        fn = os.path.join(outdir, f"{kind}-s{seed}-{i}.sql")
        with open(fn, "w") as f:
            f.write(f"-- mode={mode}\n{setup}\n\n-- JSON_TABLE:\n{jtq};\n\n-- reference:\n{refq};\n")
            f.write(f"\n/* jt: {a[1] if a[0]=='err' else len(a[1])}\n   ref: {b[1] if b[0]=='err' else len(b[1])} */\n")
        if verbose:
            print(kind, fn)
    print(json.dumps({"seed": seed, **stats}))


if __name__ == "__main__":
    main()
