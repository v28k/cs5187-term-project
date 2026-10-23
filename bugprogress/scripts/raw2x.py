import sys, psycopg
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5433
conn = psycopg.connect(f"host=localhost port={port} user=postgres dbname=postgres", autocommit=True)
setup = """
drop schema if exists r2 cascade; create schema r2; set search_path=r2;
create table t(a int, b int, j jsonb, s text);
insert into t values (1,null,'{"a":1}','x'),(2,3,'[1,2]',null);
create table pt(a int, b int) partition by list (a);
create table pt1 partition of pt for values in (1);
create table pt2 (x int, b int, a int); alter table pt2 drop column x;
alter table pt attach partition pt2 for values in (2);
create table ih(a int, b int); create table ihc(z int, b int, a int); alter table ihc inherit ih;
create function nf(x bool default true, y int default 0) returns bool language sql as 'select x';
create procedure np(x bool, inout y int default 0) language plpgsql as 'begin y := x::int; end';
create table m(a int primary key, b bool);
"""
E = ["(NULL IS NULL)", "(NULL::int IS NOT NULL)", "(NULL IS TRUE)", "(NULL::bool IS NOT UNKNOWN)",
     "nf(x => NULL IS NULL)", "nf(y => 1, x => (NULL IS DISTINCT FROM 1))", "(ROW(NULL,1) IS NULL)",
     "(b IS NULL)", "(a IS NOT NULL IS TRUE)", "nf(x => b IS NULL)"]
T = [
 "select {e} from t", "select * from t where {e} between false and true",
 "select * from t where {e} between symmetric true and false", "select * from t where {e} not between false and {e}",
 "select * from t where {e} in (true, false, {e})", "select case {e} when true then 1 when {e} then 2 end from t",
 "select a from t group by grouping sets (({e}), (a)) ", "select a from t group by cube({e}, a)",
 "select distinct on ({e}) a from t order by {e}", "select sum(a) over (partition by {e} order by {e}) from t",
 "select json_object('k': {e})", "select json_array({e}, {e})", "select json_arrayagg({e}) from t",
 "select json_objectagg(s: {e}) from t", "select json_value(j, '$.a' passing {e} as v) from t",
 "select json_exists(j, '$ ? (@ == $v)' passing {e} as v) from t",
 "select json_query(j, '$' passing {e} as v) from t",
 "select * from t, json_table(t.j, '$' passing {e} as v columns (c bool path '$v')) jt",
 "select * from t, json_table(t.j, '$' columns (c bool path '$.a' default {e} on error)) jt",
 "select json_value(j, '$.zz' returning bool default {e} on empty) from t",
 "select * from t, xmltable('/a' passing xmlparse(document '<a/>') columns c bool path '.' default {e}) x",
 "select xmlelement(name e, xmlattributes({e} as q), {e}) from t",
 "update t set (a, b) = (select {e}::int, {e}::int) where false",
 "update t set (a, b) = row({e}::int, {e}::int) where false",
 "insert into t(a) select {e}::int where false",
 "insert into m values (1, {e}) on conflict (a) do update set b = {e} and excluded.b",
 "merge into m using t on m.a = t.a when matched and {e} then update set b = {e} when not matched and {e} then insert values (t.a, {e})",
 "update pt set b = {e}::int where {e} returning {e}", "delete from ih where {e} returning {e}",
 "update ih set b = ({e})::int where {e}",
 "call np({e})", "call np(x => {e})", "call np(y => 1, x => {e})", "do $$ begin perform {e}; end $$",
 "select * from (values ({e}), ({e})) v(c)", "select {e} from t limit (case when {e} then 1 else 2 end)",
 "with recursive w(n) as (select 1 union all select n+1 from w where {e} and n < 3) select * from w",
 "select array[{e}, {e}]", "select row({e}, {e}) = row({e}, {e})", "select row({e}, 1) < row({e}, 2)",
 "select {e} is distinct from {e}", "select nullif({e}, {e})", "select coalesce({e}, {e})", "select greatest({e}, {e})",
 "select {e} = any(array[{e}])", "select {e} = all(select {e})", "select * from t where ({e}, a) in (select {e}, a from t)",
 "select ({e})::text collate \"C\"", "select format('%s', {e})", "select {e} from t order by {e} using <",
 "select 1 from t having {e}", "select count(*) filter (where {e}) from t",
 "select percentile_disc(0.5) within group (order by {e}) from t", "select string_agg(s, ',' order by {e}) from t",
 "select * from generate_series(1, 2) with ordinality as g where {e}",
 "select * from rows from (generate_series(1, case when {e} then 2 end)) x",
 "explain (costs off) select {e} from pt where {e}",
 "prepare pp as select {e}; execute pp; deallocate pp",
 "create temp table ctas as select {e} as c; drop table ctas",
 "create temp view vv as select {e} as c from t where {e}; select * from vv; drop view vv",
 "create index on pt (({e}::int)); ", "create index on ih (a) where {e} ",
 "create temp table gtab (a int, g bool generated always as ({e}) stored); drop table gtab",
 "alter table ih add column gx bool default {e}; alter table ih drop column gx",
 "alter table pt add column gy bool generated always as ({e}) virtual; alter table pt drop column gy",
 "alter table ih add constraint cx check ({e} or true); alter table ih drop constraint cx",
 "alter table pt add constraint cx check ({e} or true); alter table pt drop constraint cx",
 "alter table ih alter column b type bigint using ({e})::int; alter table ih alter column b type int",
 "alter table pt alter column b type bigint using ({e})::int; alter table pt alter column b type int",
 "create policy pol on t using ({e}) with check ({e}); drop policy pol on t",
 "create trigger trg before update on pt for each row when ({e}) execute function suppress_redundant_updates_trigger(); drop trigger trg on pt",
 "create statistics st on (({e}::int)), a from t; drop statistics st",
 "create domain dd as bool check (value = {e} or true); drop domain dd",
 "create temp table lp (a bool) partition by list (a); create temp table lp1 partition of lp for values in ({e}); drop table lp",
 "create temp table rp (a int) partition by range (a); create temp table rp1 partition of rp for values from (({e})::int) to (5); drop table rp",
 "create function ff(x bool default {e}) returns bool language sql return x; select ff(); drop function ff",
 "select * from t tablesample bernoulli (case when {e} then 100 else 0 end)",
 "select {e} from t for update", "values ({e}) except select {e}", "select {e} union select {e}",
 "select (select {e}) from t", "select * from t where exists (select 1 where {e})",
 "select * from t natural join (select a, {e} as q from t) z", "select * from t join t t2 using (a) where {e}",
 "select * from t left join lateral (select {e} as q) l on {e}",
 "select x from unnest(array[1]) x where {e} group by x having {e}",
 "select jsonb_path_query(j, '$') from t where {e}", "select {e}::text::bool",
 "select json_scalar({e})", "select json_serialize(json_object('a': {e}) returning text)",
 "select json({e}::text)", "select ({e})::jsonb", "select json_array(select {e} from t)",
 "select json_object('a' : {e} absent on null with unique keys)",
 "select json_objectagg(s : {e} absent on null with unique) from t",
 "select json_arrayagg({e} order by {e}) from t",
]
conn.execute(setup)
bad = 0
for t in T:
    for e in E:
        q = t.replace("{e}", e)
        try:
            with conn.transaction():
                conn.execute("set search_path=r2")
                conn.execute(q)
        except psycopg.Error as ex:
            st = ex.sqlstate or ""
            msg = str(ex).splitlines()[0]
            if st.startswith("XX") or "unrecognized node" in msg or "cache lookup" in msg or st == "" or "server closed" in msg:
                bad += 1
                print(st, "|", msg, "|", q)
                if conn.closed:
                    conn = psycopg.connect(f"host=localhost port={port} user=postgres dbname=postgres", autocommit=True)
        except Exception as ex:
            print("PYERR", ex, q)
            conn = psycopg.connect(f"host=localhost port={port} user=postgres dbname=postgres", autocommit=True)
print("bad", bad, "of", len(T) * len(E))
