<!-- Paste everything below into Claude. Save its JSON answer as responses/6aecabcd5e-r0.json -->

## Instructions

You extend a typed grammar that a fuzzer uses to generate SQL for PostgreSQL (assert-enabled master). The fuzzer runs every generated test case, looks for crashes, assertion failures, internal errors, and wrong results (plan-variant and metamorphic oracles), and keeps test cases that reach new features. Given one recent PostgreSQL commit, you propose grammar alternatives that make the generator reach the code that commit changed, so that thousands of variations of that SQL are tested.

## The .pgg grammar format
Parser for the ``.pgg`` grammar format.

A ``.pgg`` file is a typed context-free grammar for SQL::

    %type int  "int"  num ord w=5        # type name, SQL spelling, classes, weight
    %start stmt                          # default start rule

    expr<T>          : <4> @col(T) | <3> @lit(T) | "(" expr<T> ")" ;
    expr<T:num>      : expr<T> "+" expr<T> ;
    expr<bool>       : expr<X> "=" expr<X> | <1 ?agg_ok> agg<bool> ;
    subq<T> @scope @shape(T) : "(" SELECT @items ^from_clause ")" ;

Elements
    ``KEYWORD``        an all-uppercase word is emitted literally
    ``"text"``         quoted text is emitted literally (punctuation must be quoted)
    ``name<type>``     nonterminal, optionally with a type argument
    ``@name(args)``    builtin implemented in Python (scope, columns, literals, ...);
                       the "(" must follow the name without a space
    ``$T``             the SQL spelling of a type variable
    ``( a | b )``      group
    ``x?`` ``x?0.2``   optional (probability 0.5 or the given one)
    ``x*`` ``x+``      0..3 / 1..3 repetitions
    ``x{m,n}`` ``x{m,n/","}``   m..n repetitions, optionally separated
    ``^x``             expand ``x`` before the other elements (rendering order is unchanged),
                       e.g. FROM before the select list so the list can refer to its columns

Type arguments
    ``T``              the rule's type parameter
    ``int``            a declared type
    ``num``            a declared class: a fresh random member at every use
    ``X`` ``X:num``    an alternative-local type variable, bound at first use
    ``*`` ``*:num``    any type (of a class), fresh at every use

Alternative annotations ``<w ?flag ?!flag>``: weight, required and forbidden context flags.
Rule attributes (``@scope``, ``@scope(isolated)``, ``@scope(lateral)``, ``@set(f,..)``,
``@clear(f,..)``, ``@shape``, ``@shape(T)``, ``@frame``) apply to every variant of a rule name.

## Builtins (implemented in Python; anything else must be grammar text)
@col(T)            a visible column of type T, rendered qualified (a1.c0)
@lit(T)            a literal of type T
@dlit(T)           a literal from the data of the column the previous @col chose (its quantiles)
@table / @table(plain) / @table(t1)   a relation from the schema (or one named), bound to a fresh alias "AS aN"
@items / @items(rule, nowin)           the select list: one select_item<T> per type of the current shape, "AS c0, c1, .."
@ordinal(T)        an ORDER BY ordinal of the select list
@group_keys / (rollup) / (cube) / (sets)   GROUP BY keys; the level becomes grouped
@global_agg        the level becomes a global aggregate (no GROUP BY)
@derived_alias     alias of a derived table whose columns are c0.. of the current shape
@cte_name          name of a CTE with the current shape
@define_alias(T,..) / @define_alias(-, T, ..)  alias (+ column list) of a set-returning function / JSON_TABLE
@define_rel(name, T, ..)               make a relation visible (recursive CTE)
@join_eq           a hash/merge-joinable equality between the two inputs of the current join (@frame rules)
@sorted_agg(FUNC, T, extra..)          FUNC(e, extra ORDER BY e): order-sensitive aggregate made deterministic
@target / @target(plain) / @target(nopk)   DML / DDL target table (writable)
@target_col(T, pk|distinct|writable)   a column of the target
@insert_body / (values, one)           column list + VALUES rows or a query, respecting NOT NULL / keys
@assign            SET col = value, ...
@new_table / (partitioned|view|matview|shape)  a fresh table name (n1, n2, ..); @new_col(T, flags) / @newrel_col(T) / @fill
@fresh_name(p)     a fresh name; @target_name the target's name; @shape_list(rule) one rule<T> per shape type; @out

## Conventions the fragment must follow
* Every binary operator is parenthesised: "(" expr<int> "+" expr<int> ")".
* Column references come only from @col / @target_col (never write a column name as literal text).
* Results must not depend on row order or the plan: no LIMIT without ORDER BY, no volatile functions
  (random(), clock_timestamp(), nextval()), order-sensitive aggregates through @sorted_agg.
* Prefer new alternatives of existing rules (expr<bool>, expr<T>, from_item, select_core, setup_stmt,
  create_table, stmt, ...) with small weights (<0.5> .. <2>) over new top-level rules.
* A new rule name must not clash with existing names; attributes (@scope, @frame, ...) apply to every variant
  of a rule name, so add attributes only to new rule names.
* Do not add %type or %start lines. Types available: the %type names in the grammar below.
* Use only the builtins listed above, with the argument forms shown.
* Keep it small: 1-8 alternatives that reach the changed code; quality over coverage of the whole feature.

## Database schema (schema.yaml; the same tables exist on the server)
```yaml
# The tables of corpus/schema.sql as seen by the grammar generator.
# Column: [name, type, flags...]; types are the %type names of grammar/postgres.pgg.
# Flags: pk, notnull, identity (GENERATED ... AS IDENTITY), generated (generated column).
relations:
  t0:
    columns: [[c0, int], [c1, text], [c2, float8]]
  t1:
    columns: [[c0, int, pk, notnull], [c1, int], [c2, jsonb], [c3, int4range]]
  t2:
    columns: [[c0, bigint, identity], [c1, numeric], [c2, tstz], [c3, textarr]]
  t3:
    columns: [[c0, int, notnull], [c1, bool], [c2, date], [c3, interval], [c4, intarr], [c5, text]]
  t4:
    columns: [[c0, int], [c1, int, generated], [c2, text, generated], [c3, numeric]]
  tp:
    kind: partitioned
    columns: [[c0, int, notnull], [c1, text]]
  tl:
    kind: partitioned
    columns: [[c0, int], [c1, text]]
  ti:
    columns: [[c0, int], [c1, text]]
  v0:
    kind: view
    columns: [[c0, int], [n, bigint]]
```

## The current grammar
```
# PostgreSQL grammar for the pgfuzz grammar generator (format: pgfuzz/grammar/dsl.py).
#
# Conventions
#  * every binary operator is parenthesised, so operator precedence never changes types;
#  * every column reference is qualified (aliases a1, a2, ... are unique per statement);
#  * order-sensitive aggregates order by their own argument (@sorted_agg), so the
#    differential plan oracle never sees legitimately different results;
#  * flags: agg_ok (aggregates allowed), win_ok (window functions allowed),
#    in_agg (inside an aggregate: every column of the level may be referenced).

%type int        "int"          num ord key skey mm brin shape w=6
%type bigint     "bigint"       num ord key skey mm brin shape w=2
%type numeric    "numeric"      num ord key skey mm brin shape w=2
%type float8     "float8"       num ord key skey mm brin shape w=1.5
%type text       "text"         ord key skey mm brin spg shape w=4
%type bool       "boolean"      ord key skey shape w=2
%type date       "date"         ord key skey mm brin shape w=1
%type tstz       "timestamptz"  ord key skey mm brin shape w=1
%type interval   "interval"     ord key skey mm brin shape w=1
%type jsonb      "jsonb"        ord key skey shape w=1.5
%type int4range  "int4range"    ord key skey spg shape w=1
%type textarr    "text[]"       ord key mm arr shape w=0.7
%type intarr     "int[]"        ord key mm arr shape w=1

%start stmt

# ===================================================================== statements

stmt
  : <14> query
  | <2>  insert_stmt
  | <2>  update_stmt
  | <1>  delete_stmt
  | <1.5> merge_stmt
  | <1>  explain_stmt
  ;

setup_stmt
  : <4> create_index
  | <3> create_table
  | <1> create_view
  | <1> create_stats
  | <1> ANALYZE @table(plain)
  | <2> insert_stmt
  | <1> update_stmt
  | <1> delete_stmt
  | <1.5> alter_table
  | <1.5> set_stmt
  ;

explain_stmt
  : <2> EXPLAIN "(" COSTS OFF ")" query
  | <2> EXPLAIN "(" VERBOSE "," COSTS OFF ")" query
  | <2> EXPLAIN "(" ANALYZE "," COSTS OFF "," TIMING OFF "," SUMMARY OFF ")" query
  ;

# ===================================================================== queries

query @scope
  : <8> select_core order_by?0.3 limit_clause?0.06
  | <2> with_clause select_core order_by?0.2
  | <2> set_query
  | <1> with_clause set_query
  | <0.5> values_query
  ;

select_core
  : <6> SELECT distinct?0.12 @items ^from_clause ^where_clause?0.6
  | <3> SELECT @items ^from_clause ^where_clause?0.5 GROUP BY ^@group_keys having_clause?0.4
  | <0.7> SELECT @items ^from_clause ^where_clause?0.5 GROUP BY ^@group_keys(rollup) having_clause?0.2
  | <0.5> SELECT @items ^from_clause GROUP BY ^@group_keys(cube)
  | <0.7> SELECT @items ^from_clause ^where_clause?0.5 GROUP BY ^@group_keys(sets)
  | <2> SELECT @items ^from_clause ^where_clause?0.5 ^@global_agg having_clause?0.2
  | <0.5> SELECT @items
  ;

distinct : DISTINCT ;

limit_clause
  : LIMIT ("0" | "1" | "3" | "10")
  | LIMIT ("1" | "5") OFFSET ("1" | "3")
  | OFFSET "2"
  ;

order_by : ORDER BY order_item{1,2/","} ;
order_item : @ordinal (ASC | DESC)?0.4 (NULLS FIRST | NULLS LAST)?0.3 ;

where_clause : WHERE expr<bool> ;
having_clause @set(agg_ok) : HAVING expr<bool> ;

select_item<T> : expr<T> ;
returning_item<T> : expr<T> ;

set_query @shape : set_body @out order_by?0.3 ;
set_body
  : <4> set_arm set_op set_arm
  | <1> set_arm set_op "(" set_body ")"
  ;
set_arm @scope : select_core ;
set_op : <3> UNION | <3> UNION ALL | INTERSECT | INTERSECT ALL | EXCEPT | EXCEPT ALL ;

values_query @shape : VALUES values_row{1,4/","} @out order_by?0.2 ;
values_row : "(" @shape_list(expr) ")" ;

with_clause
  : <4> WITH cte_def{1,2/","}
  | <1> WITH RECURSIVE rec_cte
  ;
cte_def @shape : @cte_name AS materialized?0.3 "(" ^subquery ")" ;
materialized : MATERIALIZED | NOT MATERIALIZED ;
rec_cte
  : <3> "rc(c0)" AS "(" SELECT "1" UNION ALL SELECT "r.c0 + 1" FROM "rc AS r" WHERE "r.c0 <" ("5" | "20" | "100") ")" @define_rel(rc, int)
  | <1> "rc(c0)" AS "(" SELECT "1" UNION ALL SELECT "r.c0 + 1" FROM "rc AS r" WHERE "r.c0 <" ("5" | "20") ")" SEARCH (DEPTH | BREADTH) FIRST BY "c0" SET "sq" @define_rel(rc, int)
  | <1> "rc(c0)" AS "(" SELECT "1" UNION SELECT "(r.c0 * 7) % 10" FROM "rc AS r" ")" CYCLE "c0" SET "cy" USING "pth" @define_rel(rc, int)
  ;

# derived tables, CTE bodies, CTAS, views: the shape comes from the enclosing rule
subquery @scope(isolated)
  : <5> select_core order_by?0.1
  | <1> set_body
  ;

# ===================================================================== FROM

from_clause
  : <8> FROM from_item
  | <1.5> FROM @table "," LATERAL lateral_derived
  | <1.5> FROM @table "," srf_item
  ;

from_item
  : <6> @table
  | <4> joined
  | <2> derived
  | <1.5> srf_item
  ;

# parenthesised, so a join can be the right operand of another join
joined @frame
  : <5> "(" from_item (join_kind | <1> FULL JOIN) from_item ON @join_eq ")"
  | <4> "(" from_item join_kind from_item ON "(" @join_eq AND expr<bool> ")" ")"
  | <1> "(" @table CROSS JOIN srf_item ")"
  | <1> self_join
  ;

self_join @frame
  : "(" @table(t1) join_kind @table(t1) ON @join_eq ")"
  | "(" @table(t3) join_kind @table(t3) ON @join_eq ")"
  | "(" @table(t4) JOIN @table(t4) ON @join_eq ")"
  | <0.5> "(" @table(t1) join_kind @table(t1) USING "(" "c0" ")" ")"
  ;

join_kind : <3> JOIN | <3> LEFT JOIN | <1> RIGHT JOIN | <1> INNER JOIN | <0.5> LEFT OUTER JOIN ;

derived @shape : "(" subquery ")" AS @derived_alias ;
lateral_derived @shape : "(" lateral_subquery ")" AS @derived_alias ;
lateral_subquery @scope(lateral)
  : <3> select_core
  | <1> select_core ORDER BY "1" LIMIT ("1" | "2")
  ;

srf_item @frame
  : <3> GENERATE_SERIES "(" small "," small ")" AS @define_alias(int)
  | <1> UNNEST "(" expr<intarr> ")" WITH ORDINALITY AS @define_alias(int, bigint)
  | <1> UNNEST "(" expr<textarr> ")" AS @define_alias(text)
  | <1> JSONB_ARRAY_ELEMENTS "(" JSONB_BUILD_ARRAY "(" expr<*> "," expr<*> ")" ")" AS @define_alias(jsonb)
  | <1> JSONB_EACH "(" jobj ")" AS @define_alias(text, jsonb)
  | <1> JSON_TABLE "(" expr<jsonb> "," "'$[*]'" COLUMNS "(" "c0 int PATH '$.k'," "c1 text PATH '$'" ")" ")" AS @define_alias(-, int, text)
  | <0.5> JSON_TABLE "(" expr<jsonb> "," "'$.a[*]'" COLUMNS "(" "c0 FOR ORDINALITY," "c1 int PATH '$'" ")" ")" AS @define_alias(-, int, int)
  | <1> ROWS FROM "(" GENERATE_SERIES "(" "1" "," small ")" "," UNNEST "(" expr<textarr> ")" ")" AS @define_alias(int, text)
  | <0.5> "(" VALUES "(1, 'a'::text), (2, NULL::text), (NULL::int, 'c'::text)" ")" AS @define_alias(int, text)
  ;

small : "1" | "2" | "3" | "5" | "10" ;

# ===================================================================== expressions

expr<T>
  : <8> @col(T)
  | <4> @lit(T)
  | <1> CASE WHEN expr<bool> THEN expr<T> ELSE expr<T> END
  | <0.5> CASE expr<X:key> WHEN expr<X> THEN expr<T> WHEN expr<X> THEN expr<T> ELSE expr<T> END
  | <1> COALESCE "(" expr<T> "," expr<T> ")"
  | <0.4> NULLIF "(" expr<T> "," expr<T> ")"
  | <0.4> GREATEST "(" expr<T> "," expr<T> ")"
  | <0.4> LEAST "(" expr<T> "," expr<T> ")"
  | <1> scalar_sub<T>
  | <3 ?agg_ok> agg<T>
  | <1.5 ?win_ok> win<T>
  | <0.2> NULL "::" $T
  ;

expr<T:num>
  : <2> "(" expr<T> ("+" | "-") expr<T> ")"
  | <0.4> "(" expr<T> "/" NULLIF "(" expr<T> "," "0" ")" ")"
  | <0.4> "(" "-" expr<T> ")"
  | <0.4> ABS "(" expr<T> ")"
  ;

expr<int>
  : <0.5> "(" expr<int> "%" NULLIF "(" expr<int> "," "0" ")" ")"
  | <0.5> "(" "(" expr<int> "%" "100" ")" "*" "(" expr<int> "%" "100" ")" ")"
  | <1> LENGTH "(" expr<text> ")"
  | <0.3> POSITION "(" expr<text> IN expr<text> ")"
  | <0.5> CARDINALITY "(" expr<X:arr> ")"
  | <0.3> ARRAY_LENGTH "(" expr<X:arr> "," "1" ")"
  | <0.5> "(" expr<intarr> ")" "[" small "]"
  | <0.5> LOWER "(" expr<int4range> ")"
  | <0.3> UPPER "(" expr<int4range> ")"
  | <0.3> "(" expr<date> "-" expr<date> ")"
  | <0.3> EXTRACT "(" DAY FROM expr<date> ")" "::" "int"
  | <0.5> "(" expr<bigint> "%" "1000" ")" "::" "int"
  | <0.3> ASCII "(" expr<text> ")"
  | <0.3> WIDTH_BUCKET "(" expr<numeric> "," "0.0" "," "100.0" "," "10" ")"
  | <0.3> "(" JSONB_BUILD_OBJECT "(" "'k'" "," expr<int> ")" "->>" "'k'" ")" "::" "int"
  | <0.2> JSON_VALUE "(" expr<jsonb> "," "'$.k'" RETURNING "int" NULL ON ERROR ")"
  ;

expr<bigint>
  : <1> "(" expr<int> ")" "::" "bigint"
  | <0.5> "(" "(" expr<bigint> "%" "1000" ")" "*" "(" expr<bigint> "%" "1000" ")" ")"
  | <0.3> "(" "(" expr<bigint> "%" "1000" ")" "<<" ("1" | "3") ")"
  ;

expr<numeric>
  : <1> "(" expr<int> ")" "::" "numeric"
  | <0.5> "(" "(" expr<numeric> "%" "100" ")" "*" "(" expr<numeric> "%" "100" ")" ")"
  | <0.5> ROUND "(" expr<numeric> "," ("0" | "2" | "(-1)") ")"
  | <0.3> TRUNC "(" expr<numeric> ")"
  | <0.3> EXTRACT "(" (EPOCH | YEAR | DOW | MICROSECONDS) FROM expr<tstz> ")"
  | <0.3> EXTRACT "(" (EPOCH | DAY | HOUR) FROM expr<interval> ")"
  | <0.2> SCALE "(" expr<numeric> ")" "::" "numeric"
  ;

expr<float8>
  : <1> "(" expr<int> ")" "::" "float8"
  | <0.3> SQRT "(" ABS "(" expr<float8> ")" ")"
  | <0.2> CBRT "(" expr<float8> ")"
  | <0.2> FLOOR "(" expr<float8> ")"
  ;

expr<text>
  : <2> "(" expr<text> "||" expr<text> ")"
  | <1> LOWER "(" expr<text> ")"
  | <0.5> UPPER "(" expr<text> ")"
  | <1> SUBSTR "(" expr<text> "," expr<int> ")"
  | <0.3> SUBSTR "(" expr<text> "," small "," ("1" | "3") ")"
  | <0.5> REPLACE "(" expr<text> "," expr<text> "," expr<text> ")"
  | <0.3> LEFT "(" expr<text> "," small ")"
  | <0.3> MD5 "(" expr<text> ")"
  | <0.3> TRIM "(" BOTH "'a'" FROM expr<text> ")"
  | <0.5> CONCAT "(" expr<*> "," expr<*> ")"
  | <0.3> CONCAT_WS "(" "'-'" "," expr<*> "," expr<*> ")"
  | <1> "(" expr<X> ")" "::" "text"
  | <0.3> FORMAT "(" "'%s|%s'" "," expr<*> "," expr<*> ")"
  | <0.5> "(" expr<jsonb> "->>" jkey ")"
  | <0.3> JSONB_TYPEOF "(" expr<jsonb> ")"
  | <0.3> TO_CHAR "(" expr<tstz> "," "'YYYY-MM-DD HH24:MI'" ")"
  | <0.2> TO_CHAR "(" expr<numeric> "," "'FM999990.00'" ")"
  | <0.3> ARRAY_TO_STRING "(" expr<textarr> "," "','" ")"
  | <0.3> REGEXP_REPLACE "(" expr<text> "," "'[a-c]+'" "," "'X'" "," "'g'" ")"
  | <0.2> SPLIT_PART "(" expr<text> "," "','" "," ("1" | "2" | "(-1)") ")"
  | <0.2> LPAD "(" expr<text> "," small "," "'*'" ")"
  | <0.2> REVERSE "(" expr<text> ")"
  | <0.2> INITCAP "(" expr<text> ")"
  | <0.3> "(" expr<text> COLLATE '"C"' ")"
  | <0.2> JSON_VALUE "(" expr<jsonb> "," jsonpath ")"
  | <0.2> NORMALIZE "(" expr<text> ")"
  ;

expr<bool>
  : <4> "(" expr<X:key> cmp expr<X> ")"
  | <1.2> "(" @col(X:ord) cmp @dlit(X) ")"
  | <0.4> "(" @col(X:ord) BETWEEN @dlit(X) AND @dlit(X) ")"
  | <2> "(" expr<bool> AND expr<bool> ")"
  | <2> "(" expr<bool> OR expr<bool> ")"
  | <1> "(" NOT expr<bool> ")"
  | <1.5> "(" expr<X> IS NOT?0.4 NULL ")"
  | <0.7> "(" expr<X:key> IS NOT?0.5 DISTINCT FROM expr<X> ")"
  | <0.7> "(" expr<X:key> NOT?0.3 BETWEEN SYMMETRIC?0.2 expr<X> AND expr<X> ")"
  | <1> "(" expr<X:key> NOT?0.3 IN "(" expr<X>{1,4/","} ")" ")"
  | <1> "(" expr<X:key> NOT?0.3 IN in_sub<X> ")"
  | <1> "(" NOT?0.3 EXISTS exists_sub ")"
  | <0.6> "(" expr<X:key> cmp (ANY | ALL) in_sub<X> ")"
  | <0.4> "(" expr<X:skey> "=" ANY "(" ARRAY "[" expr<X>{1,3/","} "]" ")" ")"
  | <0.4> "(" expr<int> "=" ANY "(" ARRAY_CAT "(" expr<intarr> "," "'{}'::int[]" ")" ")" ")"
  | <1> "(" expr<text> NOT?0.2 (LIKE | ILIKE) like_pat ")"
  | <0.3> "(" expr<text> ("~" | "~*" | "!~") ("'^[a-f]'" | "'b.*c'" | "'[0-9]{2}'") ")"
  | <0.2> "(" expr<text> SIMILAR TO "'%(a|b)%'" ")"
  | <0.3> "(" expr<text> "^@" expr<text> ")"
  | <0.8> "(" expr<jsonb> ("@>" | "<@") expr<jsonb> ")"
  | <0.4> "(" expr<jsonb> "?" ("'k'" | "'a'" | "'x'") ")"
  | <0.3> "(" expr<jsonb> "@?" jsonpath ")"
  | <0.3> "(" expr<jsonb> "@@" ("'$.k == 1'" | "'$.a[*] > 1'" | "'exists($.a)'") ")"
  | <0.3> JSON_EXISTS "(" expr<jsonb> "," jsonpath ")"
  | <0.6> "(" expr<int4range> ("@>" | "&&" | "<<" | ">>" | "-|-" | "&<" | "&>") expr<int4range> ")"
  | <0.4> "(" expr<int4range> "@>" expr<int> ")"
  | <0.5> "(" expr<X:arr> ("@>" | "<@" | "&&") expr<X> ")"
  | <0.2> ISEMPTY "(" expr<int4range> ")"
  | <0.3> "(" expr<bool> IS NOT?0.3 (TRUE | FALSE | UNKNOWN) ")"
  | <0.3> "(" ROW "(" expr<X:key> "," expr<Y:key> ")" cmp ROW "(" expr<X> "," expr<Y> ")" ")"
  | <0.2> "(" expr<text> IS NOT?0.3 JSON (VALUE | OBJECT | ARRAY | SCALAR)?0.5 ")"
  ;

cmp : <2> "=" | "<>" | "<" | ">" | "<=" | ">=" ;
like_pat : "'a%'::text" | "'%b%'::text" | "'_'::text" | "'%'::text" | "'A_C%'::text" | "''::text" | "'%\\%'::text" ;
jkey : "'k'" | "'a'" | "0" | "1" | "(-1)" ;
jsonpath : "'$.a[*]'" | "'$.k'" | "'$.a[*] ? (@ > 1)'" | "'$.a[1]'" | "'$.a.size()'" | "'$[*] ? (@.k > 2).k'" | "'$.a[last]'" | "'$.k ? (@ > 0)'" ;
jobj : JSONB_BUILD_OBJECT "(" "'k'" "," expr<*> "," "'a'" "," JSONB_BUILD_ARRAY "(" expr<*> "," expr<*> ")" ")" ;

expr<date>
  : <1> "(" expr<date> "+" small ")"
  | <0.5> "(" expr<date> "-" small ")"
  | <0.5> "(" expr<tstz> ")" "::" "date"
  | <0.3> MAKE_DATE "(" "2024" "," ("1" | "2" | "12") "," ("1" | "28" | "29") ")"
  | <0.3> "(" DATE_TRUNC "(" ("'month'" | "'year'" | "'week'") "," expr<date> ")" ")" "::" "date"
  ;

expr<tstz>
  : <1> "(" expr<tstz> ("+" | "-") expr<interval> ")"
  | <0.5> "(" expr<date> ")" "::" "timestamptz"
  | <0.5> DATE_TRUNC "(" ("'day'" | "'hour'" | "'year'" | "'month'") "," expr<tstz> ")"
  | <0.2> TO_TIMESTAMP "(" "(" expr<int> "%" "100000" ")" ")"
  ;

expr<interval>
  : <1> "(" expr<interval> ("+" | "-") expr<interval> ")"
  | <0.5> "(" expr<tstz> "-" expr<tstz> ")"
  | <0.5> "(" expr<interval> "*" ("0" | "1" | "2" | "(-1)") ")"
  | <0.3> JUSTIFY_HOURS "(" expr<interval> ")"
  | <0.3> MAKE_INTERVAL "(" "days =>" "(" expr<int> "%" "100" ")" ")"
  | <0.3> AGE "(" expr<tstz> "," expr<tstz> ")"
  ;

expr<jsonb>
  : <1> "(" expr<jsonb> "->" jkey ")"
  | <0.5> "(" expr<jsonb> "#>" ("'{a,0}'" | "'{k}'" | "'{k,k}'") ")"
  | <1> JSONB_BUILD_OBJECT "(" "'k'" "," expr<*> ")"
  | <0.5> JSONB_BUILD_ARRAY "(" expr<*> "," expr<*> ")"
  | <0.7> TO_JSONB "(" expr<*> ")"
  | <0.5> "(" expr<jsonb> "||" expr<jsonb> ")"
  | <0.3> JSONB_SET "(" jobj "," ("'{k}'" | "'{a,0}'") "," expr<jsonb> ")"
  | <0.3> "(" jobj "-" "'k'" ")"
  | <0.3> "(" jobj "#-" "'{a,0}'" ")"
  | <0.3> JSONB_PATH_QUERY_FIRST "(" expr<jsonb> "," jsonpath ")"
  | <0.3> JSONB_PATH_QUERY_ARRAY "(" expr<jsonb> "," jsonpath ")"
  | <0.4> JSON_QUERY "(" expr<jsonb> "," jsonpath (WITH WRAPPER | WITH CONDITIONAL WRAPPER | OMIT QUOTES)?0.5 ")"
  | <0.2> JSONB_STRIP_NULLS "(" expr<jsonb> ")"
  | <0.3> JSON_OBJECT "(" "'k'" VALUE expr<X:key> RETURNING "jsonb" ")"
  | <0.3> JSON_ARRAY "(" expr<X:key> "," expr<X> RETURNING "jsonb" ")"
  | <0.2> JSONB_INSERT "(" jobj "," "'{a,0}'" "," expr<jsonb> ")"
  ;

expr<int4range>
  : <1> INT4RANGE "(" LEAST "(" expr<int> "," "0" ")" "," GREATEST "(" expr<int> "," "0" ")" ")"
  | <0.3> INT4RANGE "(" LEAST "(" expr<int> "," "10" ")" "," GREATEST "(" expr<int> "," "10" ")" "," ("'[]'" | "'(]'" | "'()'") ")"
  | <0.5> "(" expr<int4range> "*" expr<int4range> ")"
  | <0.3> RANGE_MERGE "(" expr<int4range> "," expr<int4range> ")"
  ;

expr<intarr>
  : <1> ARRAY "[" expr<int>{1,3/","} "]"
  | <0.5> "(" expr<intarr> "||" expr<int> ")"
  | <0.3> ARRAY_APPEND "(" expr<intarr> "," expr<int> ")"
  | <0.3> ARRAY_CAT "(" expr<intarr> "," expr<intarr> ")"
  | <0.3> ARRAY_REMOVE "(" expr<intarr> "," expr<int> ")"
  | <0.4> ARRAY in_sub<int>
  | <0.3> "(" expr<intarr> ")" "[" ("1" | "2") ":" ("2" | "3") "]"
  | <0.2> ARRAY_POSITIONS "(" expr<intarr> "," expr<int> ")"
  | <0.2> TRIM_ARRAY "(" ARRAY_APPEND "(" expr<intarr> "," "1" ")" "," "1" ")"
  | <0.2> ARRAY_REVERSE "(" expr<intarr> ")"
  | <0.2> ARRAY_SORT "(" expr<intarr> ")"
  ;

expr<textarr>
  : <1> ARRAY "[" expr<text>{1,3/","} "]"
  | <0.5> STRING_TO_ARRAY "(" expr<text> "," "','" ")"
  | <0.3> REGEXP_SPLIT_TO_ARRAY "(" expr<text> "," "'[ab]'" ")"
  | <0.3> "(" expr<textarr> "||" expr<textarr> ")"
  | <0.3> ARRAY_APPEND "(" expr<textarr> "," expr<text> ")"
  | <0.3> ARRAY in_sub<text>
  ;

# ---------------------------------------------------------------- subqueries

scalar_sub<T> @scope
  : <3> "(" SELECT agg<T> ^from_clause ^where_clause?0.6 ^@global_agg ")"
  | <0.3> "(" SELECT @col(T) ^from_clause ^where_clause?0.5 ORDER BY "1" LIMIT "1" ")"
  ;

in_sub<T> @scope @shape(T)
  : <4> "(" select_core ")"
  | <1> "(" set_body ")"
  ;

exists_sub @scope : "(" select_core ")" ;

# ---------------------------------------------------------------- aggregates

# (attributes apply to every variant of a rule name)
agg<T:mm> @set(in_agg) @clear(agg_ok, win_ok)
  : <0.5> MIN "(" expr<T> ")" FILTER "(" WHERE expr<bool> ")"
  | <3> MIN "(" expr<T> ")"
  | <3> MAX "(" expr<T> ")"
  | <0.4> MODE "(" ")" WITHIN GROUP "(" ORDER BY expr<T> ")"
  | <0.4> PERCENTILE_DISC "(" ("0.5" | "0" | "1" | "0.25") ")" WITHIN GROUP "(" ORDER BY expr<T> DESC?0.3 ")"
  ;

agg<bigint>
  : <3> COUNT "(" "*" ")"
  | <2> COUNT "(" expr<*> ")"
  | <1> COUNT "(" DISTINCT expr<X:key> ")"
  | <1> COUNT "(" "*" ")" FILTER "(" WHERE expr<bool> ")"
  | <2> SUM "(" expr<int> ")"
  | <0.3> BIT_OR "(" expr<bigint> ")"
  ;

agg<int>
  : <0.3> BIT_AND "(" expr<int> ")"
  | <0.3> BIT_XOR "(" expr<int> ")"
  ;

agg<numeric>
  : <1> SUM "(" expr<bigint> ")"
  | <2> SUM "(" expr<numeric> ")"
  | <1> AVG "(" expr<int> ")"
  | <1> AVG "(" expr<numeric> ")"
  | <0.5> STDDEV "(" expr<numeric> ")"
  | <0.5> VARIANCE "(" expr<int> ")"
  | <0.5> SUM "(" DISTINCT expr<numeric> ")"
  ;

agg<float8>
  : <2> SUM "(" expr<float8> ")"
  | <1> AVG "(" expr<float8> ")"
  | <0.4> STDDEV_POP "(" expr<float8> ")"
  | <0.3> CORR "(" expr<float8> "," expr<float8> ")"
  | <0.5> PERCENTILE_CONT "(" ("0.5" | "0.9") ")" WITHIN GROUP "(" ORDER BY expr<float8> ")"
  | <0.2> REGR_SLOPE "(" expr<float8> "," expr<float8> ")"
  ;

agg<bool>
  : BOOL_AND "(" expr<bool> ")"
  | BOOL_OR "(" expr<bool> ")"
  | <0.5> EVERY "(" expr<bool> ")"
  ;

agg<text>
  : <2> @sorted_agg(STRING_AGG, text, "','")
  | <0.5> STRING_AGG "(" DISTINCT expr<text> "," "','" ")"
  ;

agg<jsonb>
  : <1> @sorted_agg(JSONB_AGG, *:key)
  | <0.5> @sorted_agg(JSON_AGG, *:key) "::" "jsonb"
  ;

agg<intarr> : @sorted_agg(ARRAY_AGG, int) ;
agg<textarr> : @sorted_agg(ARRAY_AGG, text) ;
agg<int4range> : RANGE_INTERSECT_AGG "(" expr<int4range> ")" ;

# ---------------------------------------------------------------- window functions

win<bigint> @clear(win_ok)
  : <2> COUNT "(" "*" ")" OVER window
  | <2> RANK "(" ")" OVER window_ord
  | <1> DENSE_RANK "(" ")" OVER window_ord
  | <1> ROW_NUMBER "(" ")" OVER window_ord
  | <1> SUM "(" expr<int> ")" OVER window
  ;

win<int> : NTILE "(" ("2" | "3") ")" OVER window_ord ;

win<float8>
  : PERCENT_RANK "(" ")" OVER window_ord
  | CUME_DIST "(" ")" OVER window_ord
  ;

win<T:mm>
  : <2> MAX "(" expr<T> ")" OVER window
  | <1> MIN "(" expr<T> ")" OVER window
  | <1> LAG "(" expr<T> ")" OVER window_ord
  | <0.5> LEAD "(" expr<T> "," "1" "," expr<T> ")" OVER window_ord
  | <0.5> FIRST_VALUE "(" expr<T> ")" OVER window_ord
  | <0.3> NTH_VALUE "(" expr<T> "," "2" ")" OVER window_ord
  | <0.3> LAG "(" expr<T> ")" IGNORE NULLS OVER window_ord
  ;

win<numeric> : <1> SUM "(" expr<numeric> ")" OVER window | <1> AVG "(" expr<int> ")" OVER window ;

window : "(" partition_by?0.6 (ORDER BY wkey{1,2/","})?0.5 ")" ;
window_ord : "(" partition_by?0.6 ORDER BY wkey{1,2/","} frame?0.3 ")" ;
partition_by : PARTITION BY expr<*:key>{1,2/","} ;
wkey : expr<*:key> (ASC | DESC)?0.3 (NULLS FIRST | NULLS LAST)?0.2 ;
frame
  : ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  | ROWS BETWEEN "1" PRECEDING AND "1" FOLLOWING
  | RANGE BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
  | GROUPS BETWEEN "1" PRECEDING AND CURRENT ROW (EXCLUDE CURRENT ROW | EXCLUDE TIES | EXCLUDE GROUP)?0.5
  ;

# ===================================================================== DML

insert_value<T> : <4> @lit(T) | <2> expr<T> ;
assign_value<T> : <4> expr<T> ;
insert_query @scope(isolated) : <4> select_core | <1> set_body ;

insert_stmt @scope
  : <5> INSERT INTO @target @insert_body on_conflict returning?0.3
  ;
on_conflict
  : <3> ON CONFLICT DO NOTHING
  | <1> ON CONFLICT "(" @target_col(*, pk) ")" DO UPDATE SET @assign (WHERE expr<bool>)?0.3
  ;
returning
  : <3> RETURNING @items(returning_item, nowin)
  | <1> RETURNING "*"
  | <0.7> RETURNING "old." @target_col(*) "," "new." @target_col(*)
  ;

update_stmt @scope : UPDATE ^@target SET @assign ^update_from?0.3 ^where_clause?0.8 returning?0.3 ;
update_from @frame : FROM from_item ;

delete_stmt @scope : DELETE FROM ^@target ^using_clause?0.3 ^where_clause?0.9 returning?0.3 ;
using_clause @frame : USING from_item ;

merge_stmt @scope : MERGE INTO ^@target(nopk) USING ^merge_source ON expr<bool> merge_when merge_returning?0.3 ;
merge_source @frame : derived_one ;
derived_one @shape : "(" subquery_one ")" AS @derived_alias ;
subquery_one @scope(isolated) : select_core LIMIT "1" ;
merge_when
  : <3> (WHEN MATCHED AND expr<bool> THEN (UPDATE SET @assign | DELETE | DO NOTHING))?0.4
        WHEN MATCHED THEN (UPDATE SET @assign | DELETE | DO NOTHING)
        (WHEN NOT MATCHED (BY TARGET)?0.2 THEN (<3> INSERT @insert_body(values, one) | DO NOTHING))?0.5
        (WHEN NOT MATCHED BY SOURCE THEN (UPDATE SET @assign | DELETE))?0.3
  | <2> WHEN NOT MATCHED (BY TARGET)?0.2 THEN (<3> INSERT @insert_body(values, one) | DO NOTHING)
  | <1> WHEN NOT MATCHED BY SOURCE THEN (UPDATE SET @assign | DELETE)
  ;
merge_returning : RETURNING MERGE_ACTION "(" ")" "," @items(returning_item, nowin) ;

# ===================================================================== setup DDL

create_index @scope
  : <4> CREATE INDEX ON @target(plain) "(" index_col{1,2/","} ")" (INCLUDE "(" @target_col(*) ")")?0.15 (WHERE "(" @target_col(ord) IS NOT NULL ")")?0.3
  | <1> CREATE INDEX ON @target(plain) USING HASH "(" @target_col(key) ")"
  | <1> CREATE INDEX ON @target(plain) USING GIN "(" @target_col(jsonb) (JSONB_PATH_OPS)?0.4 ")"
  | <1> CREATE INDEX ON @target(plain) USING GIN "(" @target_col(arr) ")"
  | <1> CREATE INDEX ON @target(plain) USING GIST "(" @target_col(int4range) ")"
  | <1> CREATE INDEX ON @target(plain) USING BRIN "(" @target_col(brin) ")" (WITH "(" "pages_per_range = 1" ")")?0.5
  | <0.5> CREATE INDEX ON @target(plain) USING SPGIST "(" @target_col(spg) ")"
  ;
index_col
  : <3> @target_col(ord) (DESC)?0.3 (NULLS FIRST)?0.2
  | <1> "(" COALESCE "(" @target_col(X:ord) "," @target_col(X) ")" ")"
  ;

create_table @scope
  : <3> CREATE TABLE @new_table "(" new_col{1,4/","} ")" ";" @fill ";" ANALYZE @target_name
  | <1> CREATE UNLOGGED TABLE @new_table "(" new_col{1,3/","} ")" ";" @fill
  | <1> CREATE TABLE @new_table "(" @new_col(int, pk, notnull) PRIMARY KEY "," new_col{1,3/","} ")" ";" @fill ";" ANALYZE @target_name
  | <1.5> CREATE TABLE @new_table(partitioned) "(" @new_col(int, notnull) "," new_col{1,2/","} ")" PARTITION BY RANGE "(" "c0" ")"
          ";" CREATE TABLE @fresh_name(p) PARTITION OF @target_name FOR VALUES FROM "(MINVALUE) TO (100)"
          ";" CREATE TABLE @fresh_name(p) PARTITION OF @target_name FOR VALUES FROM "(100) TO (MAXVALUE)"
          ";" CREATE TABLE @fresh_name(p) PARTITION OF @target_name DEFAULT
          ";" @fill ";" ANALYZE @target_name
  | <0.7> CREATE TABLE @new_table(partitioned) "(" @new_col(int, notnull) "," new_col{1,2/","} ")" PARTITION BY HASH "(" "c0" ")"
          ";" CREATE TABLE @fresh_name(p) PARTITION OF @target_name FOR VALUES WITH "(MODULUS 2, REMAINDER 0)"
          ";" CREATE TABLE @fresh_name(p) PARTITION OF @target_name FOR VALUES WITH "(MODULUS 2, REMAINDER 1)"
          ";" @fill
  | <0.7> CREATE TABLE @new_table(partitioned) "(" @new_col(int, notnull) "," new_col{1,2/","} ")" PARTITION BY LIST "(" "c0" ")"
          ";" CREATE TABLE @fresh_name(p) PARTITION OF @target_name FOR VALUES IN "(1, 2, 3)"
          ";" CREATE TABLE @fresh_name(p) PARTITION OF @target_name DEFAULT
          ";" @fill
  | <2> ctas
  ;

new_col
  : <6> @new_col(*)
  | <1> @new_col(*, notnull) NOT NULL
  | <1> @new_col(T, generated) GENERATED ALWAYS AS "(" gen_expr<T> ")" (VIRTUAL | STORED)
  | <0.3> @new_col(int, identity) GENERATED ALWAYS AS IDENTITY
  | <0.4> @new_col(T:key) DEFAULT @lit(T)
  | <0.3> @new_col(X:key) CHECK "(" "(" @newrel_col(X) IS NOT NULL ")" OR TRUE ")"
  ;

gen_expr<T>
  : <3> @newrel_col(T)
  | <1> CASE WHEN "(" @newrel_col(X:key) IS NULL ")" THEN @lit(T) ELSE @newrel_col(T) END
  ;
gen_expr<T:num> : <2> "(" @newrel_col(T) ("+" | "-") @lit(T) ")" ;
gen_expr<text> : <2> "(" @newrel_col(text) "||" "'x'::text" ")" | LOWER "(" @newrel_col(text) ")" ;

ctas @shape : CREATE TABLE @new_table(shape) AS ^subquery ";" ANALYZE @target_name ;

create_view
  : <2> view_def
  | <1> matview_def
  ;
view_def @shape : CREATE VIEW @new_table(shape, view) AS ^subquery ;
matview_def @shape : CREATE MATERIALIZED VIEW @new_table(shape, matview) AS ^subquery ;

create_stats @scope
  : <2> CREATE STATISTICS ("(" (NDISTINCT | DEPENDENCIES | MCV) ")")?0.5 ON @target_col(key, distinct) "," @target_col(key, distinct) FROM ^@target(plain) ";" ANALYZE @target_name
  | <1> CREATE STATISTICS ON "(" COALESCE "(" @target_col(X:key) "," @target_col(X) ")" ")" FROM ^@target(plain) ";" ANALYZE @target_name
  ;

alter_table @scope
  : <2> ALTER TABLE @target(plain) ADD CHECK "(" "(" @target_col(key) IS NOT NULL ")" OR TRUE ")" NOT VALID
  | <2> ALTER TABLE @target(plain) ALTER COLUMN @target_col(*) SET STATISTICS ("0" | "10" | "1000")
  | <1> ALTER TABLE @target(plain) SET "(" ("fillfactor = 10" | "parallel_workers = 4" | "autovacuum_enabled = off") ")"
  | <1> ALTER TABLE @target(plain) ALTER COLUMN @target_col(text) SET STORAGE (EXTERNAL | MAIN)
  | <0.5> ALTER TABLE "tp" DETACH PARTITION "tp_high" ";" ALTER TABLE "tp" ATTACH PARTITION "tp_high" FOR VALUES FROM "(100) TO (MAXVALUE)"
  | <0.5> CLUSTER "t0" USING "i0"
  | <0.5> TRUNCATE @target(plain)
  ;

set_stmt
  : <3> SET LOCAL ("enable_hashjoin" | "enable_mergejoin" | "enable_nestloop" | "enable_seqscan" | "enable_indexscan"
                   | "enable_bitmapscan" | "enable_hashagg" | "enable_sort" | "enable_material" | "enable_memoize"
                   | "enable_incremental_sort" | "enable_presorted_aggregate" | "enable_indexonlyscan") "=" OFF
  | <1> SET LOCAL "plan_cache_mode" "=" ("force_generic_plan" | "force_custom_plan")
  | <1> SET LOCAL "work_mem" "=" ("'64kB'" | "'1MB'")
  | <1> SET LOCAL ("enable_partitionwise_join" | "enable_partitionwise_aggregate") "=" ON
  | <1> SET LOCAL "max_parallel_workers_per_gather" "=" ("0" | "4")
  | <1> SET LOCAL "parallel_setup_cost" "=" "0" ";" SET LOCAL "parallel_tuple_cost" "=" "0" ";" SET LOCAL "min_parallel_table_scan_size" "=" "0"
  | <0.5> SET LOCAL "random_page_cost" "=" ("'0.1'" | "'100'")
  | <0.5> SET LOCAL "cpu_tuple_cost" "=" "'10'"
  ;
```

## Equivalence rewrites
Besides grammar, you may propose rewrites for the metamorphic oracle: a template over one expression {e} of a grammar type (a %type name) that is equal to {e} for EVERY value, NULL included, and raises an error exactly when {e} does; e.g. type int, template 'CASE WHEN {e} IS NULL THEN NULL ELSE {e} END'. Target code the commit changed (constant folding, a support function, a new simplification). The fuzzer applies it to thousands of expressions; it is accepted only if it never changes a query's result on the server, so propose only exact identities.

Seeds are plain SQL against the schema above. They may create their own tables (they run inside a transaction that is rolled back). Answer only with the JSON object described by the output schema.

## user

Commit 6aecabcd5ed5 (2026-10-15): Use SPI for RI checks whose FK values need a cast function

When the FK column's type needs a cast function to reach the equality
operator's input type, the RI fast path calls that function directly.
The SPI path instead applies the cast as an expression in its query,
which takes care of the function's declared arguments, its input
collation, a NULL result, volatility, and replanning when the function
changes.  The direct call doesn't cover all of that; for example, a
NULL result raises an internal error rather than a foreign key
violation, and if the cast's function is dropped and replaced, later
checks fail with "cache lookup failed for function".  Coercions that
aren't a call to one function, array coercion and coercion via I/O,
fail outright with "no conversion function".

Rather than replicate expression evaluation, leave FK values that
aren't binary-coercible to the operator's input type to SPI.  The fast
path keeps handling cross-type operators, domains and binary-compatible
types.  As eligibility now depends on pg_cast, invalidate cached
constraint information on pg_cast changes too.

Because the check needs catalog lookups, it is made in
ri_check_fastpath_index(), which caches its result in fastpath_state
until the constraint's cached information is invalidated, rather than
for every row in ri_fastpath_is_applicable().

The two tests that used a cast function to exercise fast-path code that
still exists (metadata invalidation and the active snapshot) now use
the equality function of a custom opclass, the only user code a
fast-path check still runs.

The fast-path code that calls cast functions is now unused; the next
commit removes it.

Reported-by: Nikolay Samokhvalov <nik@postgres.ai>
Reported-by: Amit Langote <amitlangote09@gmail.com>
Reviewed-by: Matheus Alcantara <matheusssilv97@gmail.com>
Discussion: https://postgr.es/m/CAM527d9BgPjeOOYmbCBTd57R145qHCk-dzw9qNq+nOrDq1j__A@mail.gmail.com
Backpatch-through: 19

Files changed:
  src/backend/utils/adt/ri_triggers.c
  src/test/regress/expected/foreign_key.out
  src/test/regress/sql/foreign_key.sql
Functions changed: ri_check_fastpath_index, RI_FKey_check, get_ri_constraint_root, InvalidateConstraintCacheCallBack, ri_FastPathCheck, ri_LockPKTuple, ri_fastpath_is_applicable, recheck_matched_pk_tuple, ri_InitHashTables
Diff-coverage targets (your alternatives should execute these lines):
  src/backend/utils/adt/ri_triggers.c: 17 changed lines

SQL this commit added to the regression tests:
```sql
-- not be lost.  An RI check runs during the deferred firing loop and can run
-- user cast code whose DML queues a further deferred check; that check must
-- still fire.  fk_defer_main's deferred check runs a cast whose function
-- inserts a violating row into fk_defer_t2, queueing fk_defer_t2's own
-- deferred check, which must still be reported.
-- An FK check must check EXECUTE, as the referenced table's owner, on the
-- functions it applies to the FK values: the equality operator's function
-- and, for an FK needing an implicit cast function, the cast.  Validation of
-- a new constraint by a role that cannot use the bulk check (RLS is enabled
-- on the referenced table) runs per-row checks, through the fast path for
-- the operator case and through SPI for the cast case, since FK values that
-- need a cast function are not checked by the fast path.
  ADD FOREIGN KEY (a) REFERENCES pktable_acl_cast (a);	-- fails (SPI path message)
-- A STABLE equality function used by an FK check must see changes made by
-- earlier AFTER triggers, using the check's snapshot rather than the outer
-- query's snapshot.  Compare the fast path (pk_fast) with a partitioned-parent
-- SPI check (pk_spi).  The equality function of the referenced index's
-- opclass is the user code that runs during a fast-path check.
-- Considers two values equal only if a lookup row exists for them.
CREATE FUNCTION lookup_eq(a int, b int) RETURNS bool
    RETURN a = b AND EXISTS (SELECT 1 FROM lookup_rows AS r WHERE r.v = a);
CREATE OPERATOR === (LEFTARG = int, RIGHTARG = int, FUNCTION = lookup_eq);
CREATE OPERATOR CLASS lookup_ops FOR TYPE int USING btree AS
    OPERATOR 1 <, OPERATOR 2 <=, OPERATOR 3 ===, OPERATOR 4 >=, OPERATOR 5 >,
    FUNCTION 1 btint4cmp(int, int);
CREATE TABLE pk_fast (v int);
CREATE UNIQUE INDEX ON pk_fast (v lookup_ops);
CREATE TABLE pk_spi (v int) PARTITION BY RANGE (v lookup_ops);
CREATE UNIQUE INDEX ON pk_spi (v lookup_ops);
CREATE TABLE fk_fast (k int REFERENCES pk_fast(v));
CREATE TABLE fk_spi (k int REFERENCES pk_spi(v));
    INSERT INTO lookup_rows VALUES (NEW.k);
-- Both checks must succeed.  Without the check's snapshot active, the
-- STABLE equality function misses the lookup row, so no PK row matches.
INSERT INTO fk_fast VALUES (1);
INSERT INTO fk_spi VALUES (1);
-- Re-entrant FK check: DML on the same FK table from a cast function
-- The equality function of the referenced index's opclass runs while the
-- fast path scans the index.  One that performs DDL raises an invalidation
-- there, detaching the constraint's fast-path metadata while the check is
-- still using it.  This is done in a transaction that is rolled back, so that
-- other tests never see the operator class.
BEGIN;
CREATE FUNCTION fp_inval_eq(int4, int4) RETURNS bool AS $$
    RETURN $1 OPERATOR(pg_catalog.=) $2;
CREATE OPERATOR =@= (LEFTARG = int4, RIGHTARG = int4, FUNCTION = fp_inval_eq);
CREATE OPERATOR CLASS fp_inval_ops FOR TYPE int4 USING btree AS
    OPERATOR 1 pg_catalog.<, OPERATOR 2 pg_catalog.<=, OPERATOR 3 =@=,
    OPERATOR 4 pg_catalog.>=, OPERATOR 5 pg_catalog.>,
    FUNCTION 1 btint4cmp(int4, int4);
CREATE TABLE pktable_inval (a int4, b int4);
CREATE UNIQUE INDEX pktable_inval_a_b ON pktable_inval (a fp_inval_ops, b);
CREATE TABLE fktable_inval (a int4, b int4,
INSERT INTO fktable_inval VALUES (1, 1), (2, 2);
-- Confirms the equality function actually ran and raised the invalidation.
-- Without this the insert above could pass merely by not exercising the path
-- at all.
ROLLBACK;

--
-- FK values that need a coercion to reach the equality operator's input type
-- are checked through SPI, which applies the coercion as part of the query.
-- The fast path used to call the cast function directly.
--
BEGIN;
CREATE SCHEMA ri_cast;
SET LOCAL search_path = ri_cast, pg_catalog;

-- A cast that returns NULL for a non-NULL key: an FK violation, as for any
-- other key without a match, not an internal error.
CREATE TYPE ri_word AS ENUM ('one', 'none');
CREATE FUNCTION ri_word_to_int4(ri_word) RETURNS int4
    LANGUAGE sql IMMUTABLE AS $$ SELECT CASE WHEN $1::text = 'one' THEN 1 END $$;
CREATE CAST (ri_word AS int4) WITH FUNCTION ri_word_to_int4(ri_word) AS IMPLICIT;
CREATE TABLE ri_pk (id int4 PRIMARY KEY);
INSERT INTO ri_pk VALUES (1);
CREATE TABLE ri_fk (a ri_word REFERENCES ri_pk);
INSERT INTO ri_fk VALUES ('one');
SAVEPOINT s;
INSERT INTO ri_fk VALUES ('none');	-- fails
ROLLBACK TO SAVEPOINT s;

-- Replacing the cast and dropping its old function must not leave a later
-- check in this session calling the dropped function.
CREATE FUNCTION ri_word_to_int4_v2(ri_word) RETURNS int4
    LANGUAGE sql IMMUTABLE AS $$ SELECT 1 $$;
DROP CAST (ri_word AS int4);
CREATE CAST (ri_word AS int4) WITH FUNCTION ri_word_to_int4_v2(ri_word) AS IMPLICIT;
DROP FUNCTION ri_word_to_int4(ri_word);
INSERT INTO ri_fk VALUES ('none');	-- succeeds through the new cast

-- A collation-sensitive cast from a collatable type gets the input
-- collation an expression would give it.
CREATE TYPE ri_ctext;
CREATE FUNCTION ri_ctext_in(cstring) RETURNS ri_ctext
    AS 'textin' LANGUAGE internal IMMUTABLE STRICT;
CREATE FUNCTION ri_ctext_out(ri_ctext) RETURNS cstring
    AS 'textout' LANGUAGE internal IMMUTABLE STRICT;
CREATE TYPE ri_ctext (INPUT = ri_ctext_in, OUTPUT = ri_ctext_out,
                      LIKE = text, COLLATABLE = true);
CREATE FUNCTION ri_ctext_lower(ri_ctext) RETURNS text
    AS 'lower' LANGUAGE internal IMMUTABLE STRICT;
CREATE CAST (ri_ctext AS text) WITH FUNCTION ri_ctext_lower(ri_ctext) AS IMPLICIT;
CREATE TABLE ri_pk_text (k text PRIMARY KEY);
INSERT INTO ri_pk_text VALUES ('abc');
CREATE TABLE ri_fk_text (a ri_ctext REFERENCES ri_pk_text);
INSERT INTO ri_fk_text VALUES ('ABC');	-- succeeds; the cast lowercases

-- An array coercion (int2[] to int4[], allowed with an opclass declared for
-- int4[]) has no single cast function to call.
CREATE FUNCTION ri_i4a_lt(int4[], int4[]) RETURNS bool
    AS 'array_lt' LANGUAGE internal IMMUTA
```

Propose the grammar fragment and seeds.

## Output format

Answer with one JSON object matching this schema, nothing else:

```json

{
 "type": "object",
 "properties": {
  "rationale": {
   "type": "string",
   "description": "Which code paths the commit changed and which SQL reaches them (3-6 sentences)."
  },
  "grammar_fragment": {
   "type": "string",
   "description": ".pgg text: new alternatives (as new variants of existing rules) and new rules. Empty string if the existing grammar already covers the commit."
  },
  "seeds": {
   "type": "array",
   "items": {
    "type": "string"
   },
   "description": "1-5 test cases; each is one or more SQL statements separated by ';' and newlines."
  },
  "features": {
   "type": "array",
   "items": {
    "type": "string"
   },
   "description": "Short names of the SQL features the fragment targets."
  },
  "rewrites": {
   "type": "array",
   "description": "0-3 equivalence rewrites for the metamorphic oracle (see 'Equivalence rewrites'); empty if none fits the commit.",
   "items": {
    "type": "object",
    "properties": {
     "name": {
      "type": "string"
     },
     "type": {
      "type": "string"
     },
     "template": {
      "type": "string"
     },
     "why": {
      "type": "string"
     }
    },
    "required": [
     "name",
     "type",
     "template",
     "why"
    ],
    "additionalProperties": false
   }
  }
 },
 "required": [
  "rationale",
  "grammar_fragment",
  "seeds",
  "features",
  "rewrites"
 ],
 "additionalProperties": false
}

```