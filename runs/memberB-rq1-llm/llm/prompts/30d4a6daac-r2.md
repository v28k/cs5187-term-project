<!-- Paste everything below into Claude. Save its JSON answer as responses/30d4a6daac-r2.json -->

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

Commit 30d4a6daac8b (2026-10-15): Modernize our parsing of XML data in CONTENT mode.

The main goal of this patch is to get rid of our use of
xmlKeepBlanksDefault, which libxml2 has deprecated.
To do that, we want to use xmlParseInNodeContext instead of
xmlParseBalancedChunkMemory, so that we can pass an options
mask that includes XML_PARSE_NOBLANKS.

xmlParseInNodeContext wants an xmlNode rather than an xmlDoc as
context.  This gives us an opportunity for simplification though:
we can make that node be a dummy root node for xml_parse's result
document, and then attach the content node(s) as children of the root,
essentially moving the data structure hack in xmltotext_with_options
into xml_parse.  The main benefit of this is that callers no longer
need to free the content node list separately; freeing the document is
sufficient.  (There were error paths in xmltotext_with_options that
I think would have leaked that list, though they could only be
reached in OOM or similar conditions.)

We also do some fooling with doc->encoding, to be bug-compatible
with our previous behavior on as many libxml2 versions as practical.
Some small discrepancies with previous behavior are known with older
libxml2 versions.  Therefore, it seems inadvisable to back-patch this,
at least not before it's gotten a good deal of field experience.

Author: Tom Lane <tgl@sss.pgh.pa.us>
Fix-suggested-by: Andrew Dunstan <andrew@dunslane.net>
Reviewed-by: Rui Zhao <zhaorui126@gmail.com>
Discussion: https://postgr.es/m/ZR2PPFF1830B8772632FA23847D7482168FD2C62@ZR2PPFF1830B877.CHEP278.PROD.OUTLOOK.COM

Files changed:
  src/backend/utils/adt/xml.c
  src/test/regress/expected/xml.out
  src/test/regress/sql/xml.sql
Functions changed: xml_parse, xml_in, xml_recv, xmltotext_with_options, xmlparse, xml_is_document, xml_doctype_in_content, wellformed_xml
Diff-coverage targets (your alternatives should execute these lines):
  src/backend/utils/adt/xml.c: 40 changed lines

SQL this commit added to the regression tests:
```sql
-- check some encoding-dependent behaviors
-- (this is mostly checking for libxml2 bugs, not our bugs...)
DO $$
DECLARE
  result text;
BEGIN
  IF getdatabaseencoding() = 'UTF8' THEN
    -- U+FEFF after an XML declaration is content, not a byte-order mark
    result := xmlserialize(CONTENT xmlparse(CONTENT
              '<?xml version="1.0"?>' || chr(65279) || 'abc') AS text INDENT);
    IF result <> '&#xFEFF;abc' THEN
      RAISE WARNING 'U+FEFF was not preserved: %', result;
    END IF;
    -- non-ASCII characters are converted to hex entities if in data
    result := xmlserialize(CONTENT xmlparse(CONTENT
              'ni' || chr(241) || 'o') AS text INDENT);
    IF result <> 'ni&#xF1;o' THEN
      RAISE WARNING 'U+F1 was not converted to a hex entity: %', result;
    END IF;
    -- non-ASCII characters are preserved in tag attributes
    result := xmlserialize(CONTENT xmlparse(CONTENT
              '<a attr="ni' || chr(241) || 'o"/>') AS text INDENT);
    IF result <> '<a attr="ni' || chr(241) || 'o"/>' THEN
      RAISE WARNING 'U+F1 was not preserved in a tag: %', result;
    END IF;
  END IF;
END
$$;

-- IS DOCUMENT
```

Propose the grammar fragment and seeds.

## assistant

{"rationale": "Commit 30d4a6daac8b updates how PostgreSQL parses XML data in CONTENT mode by switching from xmlParseBalancedChunkMemory to xmlParseInNodeContext with XML_PARSE_NOBLANKS enabled. This affects xml_parse, xmlparse, xmlserialize, xml_is_document, xml_doctype_in_content, and wellformed_xml when processing XML in CONTENT mode or validating DOCUMENT/CONTENT well-formedness. The grammar changes introduce constructs for XMLPARSE in CONTENT/DOCUMENT modes, XMLSERIALIZE formatting, and expressions involving the IS DOCUMENT predicate and XML content validation functions. These reach the updated libxml2 parsing paths and error checks in src/backend/utils/adt/xml.c.", "grammar_fragment": "expr<text>\n  : <0.5> XMLSERIALIZE \"(\" (DOCUMENT | CONTENT) XMLPARSE \"(\" (DOCUMENT | CONTENT) expr<text> xml_space?0.4 \")\" AS \"text\" INDENT?0.4 \")\"\n  | <0.3> \"(\" XMLPARSE \"(\" CONTENT expr<text> \")\" \"::\" \"text\" \")\"\n  ;\n\nxml_space : PRESERVE WHITESPACE | STRIP WHITESPACE ;\n\nexpr<bool>\n  : <0.4> \"(\" \"(\" expr<text> \"::xml\" \")\" IS NOT?0.3 DOCUMENT \")\"\n  | <0.3> \"(\" XML_IS_WELLFORMED_CONTENT \"(\" expr<text> \")\" \")\"\n  | <0.3> \"(\" XML_IS_WELLFORMED_DOCUMENT \"(\" expr<text> \")\" \")\"\n  ;\n", "seeds": ["SELECT XMLPARSE(CONTENT '<?xml version=\"1.0\"?>' || chr(65279) || 'abc') IS DOCUMENT;", "SELECT XMLSERIALIZE(CONTENT XMLPARSE(CONTENT '<a>1</a><b>2</b>') AS text INDENT);", "SELECT c1, XML_IS_WELLFORMED_CONTENT(c1), (c1::xml) IS DOCUMENT FROM t0 WHERE c1 IS NOT NULL;"], "features": ["xmlparse", "xmlserialize", "is_document", "xml_is_wellformed"], "rewrites": []}

## user

Your proposal did not pass the validation gate. Findings:
- parse: "ok"
- reachability: {"uses": 1298, "per_alternative": {"expr:632": "27/457", "expr:633": "23/290", "xml_space:636": "4/77", "expr:639": "26/157", "expr:640": "0/121", "expr:641": "0/116"}}
- validity: {"rate": 0.066, "top_errors": {"semantic_error: function xml_is_wellformed_content(text) does not exist": 77, "semantic_error: function xml_is_wellformed_document(text) does not exist": 66, "runtime_error: invalid XML document": 28, "runtime_error: not an XML document": 7}}
- seeds: [{"seed": 0, "ok": true, "outcome": "ok", "errors": []}, {"seed": 1, "ok": true, "outcome": "ok", "errors": []}, {"seed": 2, "ok": false, "outcome": "semantic_error", "errors": ["stmt 0: 42883 function xml_is_wellformed_content(text) does not exist"]}]
- coverage: {"with_proposal": {"covered": 19, "executable": 23, "ratio": 0.8261, "files": {"src/backend/utils/adt/xml.c": {"executable": 23, "covered": 19}}}, "baseline": {"covered": 0, "executable": 23, "ratio": 0.0, "files": {"src/backend/utils/adt/xml.c": {"executable": 23, "covered": 0}}}, "gain_lines": 19}
Fix the fragment (and seeds) and answer again with the complete JSON object.

## assistant

{"rationale": "Commit 30d4a6daac8b updates how PostgreSQL parses XML data in CONTENT mode by switching from xmlParseBalancedChunkMemory to xmlParseInNodeContext with XML_PARSE_NOBLANKS enabled. This affects xml_parse, xmlparse, xmlserialize, xml_is_document, xml_doctype_in_content, and wellformed_xml when processing XML in CONTENT mode or validating DOCUMENT/CONTENT well-formedness. The updated grammar fragment constructs well-formed XML string wrappers to prevent semantic parsing errors while reaching XMLPARSE in CONTENT/DOCUMENT modes, XMLSERIALIZE formatting, IS DOCUMENT predicates, and xml_is_wellformed validation.", "grammar_fragment": "expr<text>\n  : <0.5> XMLSERIALIZE \"(\" (DOCUMENT | CONTENT) XMLPARSE \"(\" (DOCUMENT | CONTENT) xml_text_expr xml_space?0.4 \")\" AS \"text\" INDENT?0.4 \")\"\n  | <0.3> \"(\" XMLPARSE \"(\" CONTENT xml_text_expr \")\" \"::\" \"text\" \")\"\n  ;\n\nxml_space : PRESERVE WHITESPACE | STRIP WHITESPACE ;\n\nxml_text_expr\n  : <3> CONCAT \"(\" \"'<a>'\" \",\" expr<text> \",\" \"'</a>'\" \")\"\n  | <2> \"(\" \"'<?xml version=\\\"1.0\\\"?>'\" \"||\" \"(\" \"chr(65279)\" \"||\" \"'abc'\" \")\" \")\"\n  | <2> CONCAT \"(\" \"'<a attr=\\\"x\\\">'\" \",\" expr<text> \",\" \"'</a>'\" \")\"\n  | <1> \"'<a>1</a><b>2</b>'\"\n  ;\n\nexpr<bool>\n  : <0.4> \"(\" \"(\" XMLPARSE \"(\" CONTENT xml_text_expr \")\" \")\" IS NOT?0.3 DOCUMENT \")\"\n  | <0.4> \"(\" XML_IS_WELLFORMED \"(\" xml_text_expr \")\" \")\"\n  ;\n", "seeds": ["SELECT XMLSERIALIZE(CONTENT XMLPARSE(CONTENT '<?xml version=\"1.0\"?>' || chr(65279) || 'abc') AS text INDENT);", "SELECT (XMLPARSE(CONTENT CONCAT('<a>', c1, '</a>'))) IS DOCUMENT FROM t0 WHERE c1 IS NOT NULL;", "SELECT xml_is_wellformed(CONCAT('<a>', c1, '</a>')) FROM t0 WHERE c1 IS NOT NULL;"], "features": ["xmlparse", "xmlserialize", "is_document", "xml_is_wellformed"], "rewrites": []}

## user

Your proposal did not pass the validation gate. Findings:
- parse: "line 639: unexpected character '\\\\'"
- seeds: [{"seed": 0, "ok": true, "outcome": "ok", "errors": []}, {"seed": 1, "ok": true, "outcome": "ok", "errors": []}, {"seed": 2, "ok": false, "outcome": "semantic_error", "errors": ["stmt 0: 42883 function xml_is_wellformed(text) does not exist"]}]
- coverage: {"with_proposal": {"covered": 19, "executable": 23, "ratio": 0.8261, "files": {"src/backend/utils/adt/xml.c": {"executable": 23, "covered": 19}}}, "baseline": {"covered": 0, "executable": 23, "ratio": 0.0, "files": {"src/backend/utils/adt/xml.c": {"executable": 23, "covered": 0}}}, "gain_lines": 19}
Fix the fragment (and seeds) and answer again with the complete JSON object.

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