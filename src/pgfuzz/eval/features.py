"""SQL feature coverage.

Code coverage says *which server code* ran; feature coverage says *which SQL
constructs* the fuzzer exercised. Both are reported because a generator can
raise line coverage by hammering one construct while never touching others.

Features are detected by a lightweight PostgreSQL-aware tokenizer (strings,
dollar quotes, quoted identifiers and comments are stripped first), so detection
is fast enough to run on every statement. The catalog is fixed, which makes
"feature coverage = features seen / catalog size" comparable across runs.
Only statements that got past the parser are counted (a rejected statement
exercises the lexer and grammar, not the feature).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from typing import Callable, Iterable

_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<lcomment>--[^\n]*)
  | (?P<bcomment>/\*.*?(?:\*/|\Z))
  | (?P<dollar>\$(?P<tag>[A-Za-z_][A-Za-z_0-9]*)?\$.*?(?:\$(?(tag)(?P=tag))\$|\Z))
  | (?P<estring>[Ee]'(?:[^'\\]|\\.|'')*'?)
  | (?P<string>(?:[BbXxNn]|[Uu]&)?'(?:[^']|'')*'?)
  | (?P<qident>(?:[Uu]&)?"(?:[^"]|"")*"?)
  | (?P<param>\$\d+)
  | (?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
  | (?P<word>[A-Za-z_\x80-\uffff][A-Za-z_0-9$\x80-\uffff]*)
  | (?P<op>::|->>|->|\#>>|\#>|@>|<@|&&|\|\||<=|>=|<>|!=|!~~\*|!~~|~~\*|~~|!~\*|!~|~\*|@@|[-+*/%^<>=~!@\#&|`?.,;:()\[\]{}])
    """,
    re.X | re.S,
)

KEYWORDS = frozenset(
    """
    ABORT ALL ALTER ANALYZE AND ANY ARRAY AS ASC ASYMMETRIC AT BEGIN BETWEEN BIGINT BOOLEAN BOTH BY CALL
    CASCADE CASE CAST CHECK CLUSTER COLLATE COLUMN COMMENT COMMIT CONCURRENTLY CONFLICT CONSTRAINT COPY
    CREATE CROSS CUBE CURRENT CURRENT_DATE CURRENT_TIMESTAMP CURSOR DEALLOCATE DECLARE DEFAULT DEFERRABLE
    DELETE DESC DISTINCT DO DOMAIN DROP ELSE END ENUM ESCAPE EXCEPT EXCLUDE EXECUTE EXISTS EXPLAIN EXTENSION
    FALSE FETCH FILTER FIRST FOLLOWING FOR FOREIGN FROM FULL FUNCTION GENERATED GRANT GROUP GROUPING GROUPS
    HAVING IF ILIKE IN INDEX INHERITS INNER INSERT INTERSECT INTERVAL INTO IS ISNULL JOIN JSON JSON_TABLE KEY LANGUAGE
    LAST LATERAL LEADING LEFT LIKE LIMIT LISTEN LOCK MATCHED MATERIALIZED MERGE NATURAL NO NOT NOTHING NOTIFY
    NOTNULL NULL NULLIF NULLS OF OFFSET ON ONLY OR ORDER ORDINALITY OTHERS OUTER OVER OVERLAPS PARTITION POLICY PRECEDING
    PREPARE PRIMARY PROCEDURE RANGE RECURSIVE REFERENCES REFRESH REINDEX RELEASE RENAME REPLACE RESET RESTRICT
    RETURNING RETURNS REVOKE RIGHT ROLLBACK ROLLUP ROW ROWS RULE SAVEPOINT SCHEMA SECURITY SELECT SEQUENCE SET
    SETS SHARE SIMILAR SOME STORED SYMMETRIC TABLE TABLESAMPLE TEMP TEMPORARY THEN TIES TO TRAILING TRIGGER TRUE
    TRUNCATE TYPE UNBOUNDED UNION UNIQUE UNLOGGED UPDATE USING VACUUM VALUES VIEW WHEN WHERE WINDOW WITH WITHIN
    WITHOUT
    """.split()
)

AGGREGATES = frozenset(
    "COUNT SUM AVG MIN MAX ARRAY_AGG STRING_AGG JSON_AGG JSONB_AGG JSON_OBJECT_AGG JSONB_OBJECT_AGG BOOL_AND "
    "BOOL_OR EVERY BIT_AND BIT_OR XMLAGG STDDEV STDDEV_POP STDDEV_SAMP VARIANCE VAR_POP VAR_SAMP CORR COVAR_POP "
    "COVAR_SAMP REGR_SLOPE RANGE_AGG RANGE_INTERSECT_AGG ANY_VALUE".split()
)
ORDERED_SET_AGGREGATES = frozenset("PERCENTILE_CONT PERCENTILE_DISC MODE RANK DENSE_RANK PERCENT_RANK CUME_DIST".split())
WINDOW_FUNCTIONS = frozenset("ROW_NUMBER RANK DENSE_RANK PERCENT_RANK CUME_DIST NTILE LAG LEAD FIRST_VALUE LAST_VALUE NTH_VALUE".split())
SRF = frozenset("GENERATE_SERIES UNNEST GENERATE_SUBSCRIPTS JSON_EACH JSONB_EACH JSONB_ARRAY_ELEMENTS JSON_ARRAY_ELEMENTS REGEXP_MATCHES JSONB_TO_RECORDSET".split())
RANGE_TYPES = frozenset("INT4RANGE INT8RANGE NUMRANGE TSRANGE TSTZRANGE DATERANGE INT4MULTIRANGE INT8MULTIRANGE NUMRANGE DATEMULTIRANGE".split())
FTS = frozenset("TO_TSVECTOR TO_TSQUERY PLAINTO_TSQUERY WEBSEARCH_TO_TSQUERY TSVECTOR TSQUERY TS_RANK".split())
GEOMETRIC = frozenset("POINT LINE LSEG BOX PATH POLYGON CIRCLE".split())
NETWORK = frozenset("INET CIDR MACADDR MACADDR8".split())
XML_FUNCS = frozenset("XML XMLPARSE XMLELEMENT XMLFOREST XMLAGG XPATH XMLTABLE XMLSERIALIZE".split())
JSON_FUNCS_PREFIX = ("JSON", "JSONB", "TO_JSON", "ROW_TO_JSON", "ARRAY_TO_JSON")
INDEX_METHODS = frozenset("BTREE HASH GIST SPGIST GIN BRIN".split())

_STRING_TOKENS = ("dollar", "estring", "string")
_SKIP = ("ws", "lcomment", "bcomment")


def tokenize(sql: str) -> list[tuple[str, str]]:
    out = []
    for m in _TOKEN.finditer(sql):
        kind = m.lastgroup
        if kind == "tag":
            kind = "dollar"
        if kind in _SKIP:
            continue
        out.append((kind, m.group()))
    return out


def statement_shape(sql: str) -> str:
    """Abstract a statement to its structure: keywords and operators kept,
    identifiers -> ``id``, literals -> ``?``. Used for query-diversity counts and
    weak crash signatures."""
    parts = []
    for kind, text in tokenize(sql):
        if kind == "word":
            up = text.upper()
            parts.append(up if up in KEYWORDS else "id")
        elif kind == "qident":
            parts.append("id")
        elif kind in _STRING_TOKENS or kind in ("number", "param"):
            parts.append("?")
        else:
            parts.append(text)
    return " ".join(parts)


@dataclass
class StmtView:
    """Upper-cased word/operator stream of one statement, literals replaced by ``?``."""

    words: list[str]

    @classmethod
    def of(cls, sql: str) -> "StmtView":
        words = []
        for kind, text in tokenize(sql):
            if kind == "word":
                words.append(text.upper())
            elif kind == "qident":
                words.append("<ID>")
            elif kind in _STRING_TOKENS:
                words.append("<STR>")
            elif kind in ("number", "param"):
                words.append("<NUM>")
            else:
                words.append(text)
        return cls(words)

    @cached_property
    def wordset(self) -> frozenset[str]:
        return frozenset(self.words)

    def has(self, *seq: str) -> bool:
        n = len(seq)
        if n == 1:
            return seq[0] in self.wordset
        if seq[0] not in self.wordset:
            return False
        w = self.words
        return any(w[i : i + n] == list(seq) for i in range(len(w) - n + 1))

    def any(self, names: Iterable[str]) -> bool:
        return not self.wordset.isdisjoint(names)

    def call(self, names: Iterable[str]) -> bool:
        names = set(names)
        w = self.words
        return any(w[i] in names and w[i + 1] == "(" for i in range(len(w) - 1))

    @cached_property
    def kind(self) -> str:
        """Main statement verb; ``WITH ... SELECT`` resolves to ``SELECT``."""
        w = self.words
        if not w:
            return ""
        if w[0] == "(":
            return next((x for x in w if x not in ("(",)), "")
        if w[0] != "WITH":
            return w[0]
        depth = 0
        for x in w[1:]:
            if x == "(":
                depth += 1
            elif x == ")":
                depth -= 1
            elif depth == 0 and x in ("SELECT", "INSERT", "UPDATE", "DELETE", "MERGE", "VALUES", "TABLE"):
                return x
        return "WITH"

    def create_target(self) -> str:
        """Object kind of a CREATE statement, skipping modifiers."""
        skip = {"OR", "REPLACE", "TEMP", "TEMPORARY", "UNLOGGED", "UNIQUE", "GLOBAL", "LOCAL", "RECURSIVE",
                "MATERIALIZED", "CONSTRAINT", "TRUSTED", "PROCEDURAL", "DEFAULT"}
        for x in self.words[1:6]:
            if x not in skip:
                if x == "VIEW" and self.has("MATERIALIZED", "VIEW"):
                    return "MATVIEW"
                return x
        return ""


Matcher = Callable[[StmtView], bool]


def _stmt(*verbs: str) -> Matcher:
    return lambda s: s.kind in verbs


def _create(*targets: str) -> Matcher:
    return lambda s: s.kind == "CREATE" and s.create_target() in targets


def _json(s: StmtView) -> bool:
    if s.any(("->", "->>", "#>", "#>>", "JSON", "JSONB", "JSON_TABLE")):
        return True
    return any(w.startswith(JSON_FUNCS_PREFIX) for w in s.wordset)


def _subquery_in_from(s: StmtView) -> bool:
    w = s.words
    return any(w[i] in ("FROM", "JOIN", ",", "LATERAL") and w[i + 1] == "(" and w[i + 2] in ("SELECT", "VALUES", "WITH")
               for i in range(len(w) - 2))


def _scalar_subquery(s: StmtView) -> bool:
    w = s.words
    return any(w[i] == "(" and w[i + 1] == "SELECT" and (i == 0 or w[i - 1] not in ("FROM", "JOIN", ",", "IN", "EXISTS", "LATERAL", "ANY", "ALL", "SOME", "AS"))
               for i in range(len(w) - 1))


# Ordered, fixed catalog: (feature id, matcher). Grouped by prefix.
CATALOG: list[tuple[str, Matcher]] = [
    # statement kinds
    ("stmt:select", _stmt("SELECT")),
    ("stmt:values", _stmt("VALUES")),
    ("stmt:table", _stmt("TABLE")),
    ("stmt:insert", _stmt("INSERT")),
    ("stmt:update", _stmt("UPDATE")),
    ("stmt:delete", _stmt("DELETE")),
    ("stmt:merge", _stmt("MERGE")),
    ("stmt:create_table", _create("TABLE")),
    ("stmt:create_table_as", lambda s: s.kind == "CREATE" and s.create_target() == "TABLE" and s.has("AS") and s.any(("SELECT", "VALUES"))),
    ("stmt:create_index", _create("INDEX")),
    ("stmt:create_view", _create("VIEW")),
    ("stmt:create_matview", _create("MATVIEW")),
    ("stmt:create_function", _create("FUNCTION", "PROCEDURE")),
    ("stmt:create_trigger", _create("TRIGGER")),
    ("stmt:create_type", _create("TYPE")),
    ("stmt:create_domain", _create("DOMAIN")),
    ("stmt:create_sequence", _create("SEQUENCE")),
    ("stmt:create_rule", _create("RULE")),
    ("stmt:create_policy", _create("POLICY")),
    ("stmt:create_statistics", _create("STATISTICS")),
    ("stmt:alter_table", lambda s: s.kind == "ALTER" and s.has("TABLE")),
    ("stmt:drop", _stmt("DROP")),
    ("stmt:truncate", _stmt("TRUNCATE")),
    ("stmt:vacuum", _stmt("VACUUM")),
    ("stmt:analyze", _stmt("ANALYZE", "ANALYSE")),
    ("stmt:cluster", _stmt("CLUSTER")),
    ("stmt:reindex", _stmt("REINDEX")),
    ("stmt:refresh_matview", _stmt("REFRESH")),
    ("stmt:explain", _stmt("EXPLAIN")),
    ("stmt:explain_analyze", lambda s: s.kind == "EXPLAIN" and s.has("ANALYZE")),
    ("stmt:prepare", _stmt("PREPARE")),
    ("stmt:execute", _stmt("EXECUTE")),
    ("stmt:copy", _stmt("COPY")),
    ("stmt:set", _stmt("SET", "RESET")),
    ("stmt:transaction", _stmt("BEGIN", "START", "COMMIT", "ROLLBACK", "END", "ABORT")),
    ("stmt:savepoint", _stmt("SAVEPOINT", "RELEASE")),
    ("stmt:cursor", _stmt("DECLARE", "FETCH", "MOVE", "CLOSE")),
    ("stmt:lock", _stmt("LOCK")),
    ("stmt:do", _stmt("DO")),
    ("stmt:call", _stmt("CALL")),
    ("stmt:grant_revoke", _stmt("GRANT", "REVOKE")),
    ("stmt:comment", _stmt("COMMENT")),
    ("stmt:listen_notify", _stmt("LISTEN", "NOTIFY", "UNLISTEN")),
    # query structure
    ("cte", lambda s: s.words[:1] == ["WITH"] or s.has("WITH", "RECURSIVE")),
    ("cte:recursive", lambda s: s.has("WITH", "RECURSIVE")),
    ("cte:materialized", lambda s: s.has("AS", "MATERIALIZED") or s.has("NOT", "MATERIALIZED")),
    ("cte:dml", lambda s: s.words[:1] == ["WITH"] and s.kind in ("SELECT",) and s.any(("INSERT", "UPDATE", "DELETE")) and s.has("RETURNING")),
    ("join:inner", lambda s: s.has("JOIN") and not s.any(("LEFT", "RIGHT", "FULL", "CROSS", "NATURAL")) or s.has("INNER", "JOIN")),
    ("join:left", lambda s: s.has("LEFT", "JOIN") or s.has("LEFT", "OUTER", "JOIN")),
    ("join:right", lambda s: s.has("RIGHT", "JOIN") or s.has("RIGHT", "OUTER", "JOIN")),
    ("join:full", lambda s: s.has("FULL", "JOIN") or s.has("FULL", "OUTER", "JOIN")),
    ("join:cross", lambda s: s.has("CROSS", "JOIN")),
    ("join:natural", lambda s: s.has("NATURAL")),
    ("join:using", lambda s: s.has("JOIN") and s.has("USING", "(")),
    ("join:lateral", lambda s: s.has("LATERAL")),
    ("subquery:from", _subquery_in_from),
    ("subquery:scalar", _scalar_subquery),
    ("subquery:exists", lambda s: s.has("EXISTS", "(")),
    ("subquery:in", lambda s: s.has("IN", "(", "SELECT")),
    ("subquery:any_all", lambda s: any(s.has(q, "(", "SELECT") for q in ("ANY", "ALL", "SOME"))),
    ("setop:union", lambda s: s.has("UNION")),
    ("setop:union_all", lambda s: s.has("UNION", "ALL")),
    ("setop:intersect", lambda s: s.has("INTERSECT")),
    ("setop:except", lambda s: s.has("EXCEPT")),
    ("distinct", lambda s: s.has("DISTINCT")),
    ("distinct:on", lambda s: s.has("DISTINCT", "ON")),
    ("where", lambda s: s.has("WHERE")),
    ("group_by", lambda s: s.has("GROUP", "BY")),
    ("group_by:grouping_sets", lambda s: s.has("GROUPING", "SETS")),
    ("group_by:rollup", lambda s: s.has("ROLLUP", "(")),
    ("group_by:cube", lambda s: s.has("CUBE", "(")),
    ("having", lambda s: s.has("HAVING")),
    ("order_by", lambda s: s.has("ORDER", "BY")),
    ("order_by:nulls", lambda s: s.has("NULLS", "FIRST") or s.has("NULLS", "LAST")),
    ("limit", lambda s: s.has("LIMIT")),
    ("offset", lambda s: s.has("OFFSET")),
    ("fetch_first", lambda s: s.has("FETCH", "FIRST") or s.has("FETCH", "NEXT")),
    ("fetch_with_ties", lambda s: s.has("WITH", "TIES")),
    ("locking_clause", lambda s: s.kind == "SELECT" and (s.has("FOR", "UPDATE") or s.has("FOR", "SHARE") or s.has("FOR", "NO", "KEY") or s.has("FOR", "KEY", "SHARE"))),
    ("tablesample", lambda s: s.has("TABLESAMPLE")),
    ("values_list", lambda s: s.has("VALUES", "(")),
    ("returning", lambda s: s.has("RETURNING")),
    ("on_conflict", lambda s: s.has("ON", "CONFLICT")),
    ("on_conflict:update", lambda s: s.has("DO", "UPDATE")),
    ("merge:matched", lambda s: s.kind == "MERGE" and s.has("WHEN", "MATCHED")),
    ("merge:not_matched", lambda s: s.kind == "MERGE" and s.has("WHEN", "NOT", "MATCHED")),
    # expressions and functions
    ("window:over", lambda s: s.has("OVER")),
    ("window:named", lambda s: s.has("WINDOW")),
    ("window:frame", lambda s: s.has("OVER") and any(s.has(f, "BETWEEN") for f in ("ROWS", "RANGE", "GROUPS"))),
    ("window:exclude", lambda s: s.has("EXCLUDE")),
    ("window:function", lambda s: s.call(WINDOW_FUNCTIONS)),
    ("agg", lambda s: s.call(AGGREGATES)),
    ("agg:distinct", lambda s: any(s.has(a, "(", "DISTINCT") for a in AGGREGATES & s.wordset)),
    ("agg:filter", lambda s: s.has("FILTER", "(", "WHERE")),
    ("agg:within_group", lambda s: s.has("WITHIN", "GROUP")),
    ("agg:ordered", lambda s: s.call(ORDERED_SET_AGGREGATES) and s.has("WITHIN", "GROUP")),
    ("agg:order_by_arg", lambda s: s.call(AGGREGATES) and s.has("ORDER", "BY") and not s.has("OVER")),
    ("grouping_fn", lambda s: s.has("GROUPING", "(")),
    ("srf", lambda s: s.call(SRF)),
    ("srf:ordinality", lambda s: s.has("WITH", "ORDINALITY")),
    ("expr:case", lambda s: s.has("CASE")),
    ("expr:cast", lambda s: s.has("CAST") or s.has("::")),
    ("expr:coalesce_nullif", lambda s: s.any(("COALESCE", "NULLIF", "GREATEST", "LEAST"))),
    ("expr:is_distinct", lambda s: s.has("IS", "DISTINCT", "FROM") or s.has("IS", "NOT", "DISTINCT")),
    ("expr:is_null", lambda s: s.has("IS", "NULL") or s.has("IS", "NOT", "NULL") or s.any(("ISNULL", "NOTNULL"))),
    ("expr:is_bool", lambda s: s.has("IS", "TRUE") or s.has("IS", "FALSE") or s.has("IS", "UNKNOWN")),
    ("expr:between", lambda s: s.has("BETWEEN") and not s.has("OVER")),
    ("expr:in_list", lambda s: s.has("IN", "(") and not s.has("IN", "(", "SELECT")),
    ("expr:like", lambda s: s.any(("LIKE", "ILIKE", "~~", "~~*", "!~~", "!~~*"))),
    ("expr:similar", lambda s: s.has("SIMILAR", "TO")),
    ("expr:regex", lambda s: s.any(("~", "~*", "!~", "!~*")) or s.call(("REGEXP_REPLACE", "REGEXP_MATCH", "REGEXP_MATCHES", "REGEXP_SUBSTR"))),
    ("expr:row", lambda s: s.has("ROW", "(")),
    ("expr:array", lambda s: s.has("ARRAY") or s.has("[")),
    ("expr:array_ops", lambda s: s.any(("@>", "<@", "&&"))),
    ("expr:json", _json),
    ("expr:json_table", lambda s: s.has("JSON_TABLE")),
    ("expr:range", lambda s: s.any(RANGE_TYPES)),
    ("expr:fts", lambda s: s.has("@@") or s.any(FTS)),
    ("expr:xml", lambda s: s.any(XML_FUNCS)),
    ("expr:geometric", lambda s: s.any(GEOMETRIC)),
    ("expr:network", lambda s: s.any(NETWORK)),
    ("expr:interval_time", lambda s: s.any(("INTERVAL", "TIMESTAMP", "TIMESTAMPTZ", "DATE", "TIME", "TIMETZ", "AT"))),
    ("expr:numeric", lambda s: s.any(("NUMERIC", "DECIMAL", "MONEY"))),
    ("expr:collate", lambda s: s.has("COLLATE")),
    ("expr:param", lambda s: "<NUM>" in s.wordset and s.kind in ("PREPARE", "EXECUTE")),
    # DDL properties
    ("ddl:temp", lambda s: s.kind == "CREATE" and s.any(("TEMP", "TEMPORARY"))),
    ("ddl:unlogged", lambda s: s.kind == "CREATE" and s.has("UNLOGGED")),
    ("ddl:primary_key", lambda s: s.has("PRIMARY", "KEY")),
    ("ddl:foreign_key", lambda s: s.has("REFERENCES")),
    ("ddl:unique", lambda s: s.kind in ("CREATE", "ALTER") and s.has("UNIQUE")),
    ("ddl:check", lambda s: s.kind in ("CREATE", "ALTER") and s.has("CHECK", "(")),
    ("ddl:exclude", lambda s: s.kind in ("CREATE", "ALTER") and s.has("EXCLUDE", "USING")),
    ("ddl:default", lambda s: s.kind in ("CREATE", "ALTER") and s.has("DEFAULT")),
    ("ddl:generated", lambda s: s.has("GENERATED")),
    ("ddl:identity", lambda s: s.has("AS", "IDENTITY") or s.has("GENERATED", "ALWAYS", "AS", "IDENTITY") or s.has("GENERATED", "BY", "DEFAULT")),
    ("ddl:partitioned", lambda s: s.kind == "CREATE" and s.has("PARTITION", "BY")),
    ("ddl:partition_of", lambda s: s.has("PARTITION", "OF") or s.has("ATTACH", "PARTITION")),
    ("ddl:inherits", lambda s: s.has("INHERITS")),
    ("ddl:index_partial", lambda s: s.kind == "CREATE" and s.create_target() == "INDEX" and s.has("WHERE")),
    ("ddl:index_expression", lambda s: s.kind == "CREATE" and s.create_target() == "INDEX" and s.has("(", "(")),
    ("ddl:index_include", lambda s: s.kind == "CREATE" and s.create_target() == "INDEX" and s.has("INCLUDE")),
    ("ddl:index_method", lambda s: s.kind == "CREATE" and s.create_target() == "INDEX" and s.has("USING") and s.any(INDEX_METHODS)),
    ("ddl:concurrently", lambda s: s.has("CONCURRENTLY")),
    ("ddl:row_security", lambda s: s.has("ROW", "LEVEL", "SECURITY")),
    ("ddl:alter_column_type", lambda s: s.kind == "ALTER" and s.has("TYPE") and s.has("ALTER", "COLUMN")),
    ("ddl:plpgsql", lambda s: s.has("PLPGSQL") or s.kind == "DO"),
    ("ddl:sql_function", lambda s: s.kind == "CREATE" and s.has("LANGUAGE", "SQL")),
    ("ddl:enum", lambda s: s.has("AS", "ENUM")),
]

FEATURE_IDS: tuple[str, ...] = tuple(name for name, _ in CATALOG)


def features_of(sql: str) -> frozenset[str]:
    view = StmtView.of(sql)
    if not view.words:
        return frozenset()
    found = set()
    for name, match in CATALOG:
        try:
            if match(view):
                found.add(name)
        except IndexError:
            continue
    return frozenset(found)


def feature_pairs(features: Iterable[str]) -> set[tuple[str, str]]:
    """Unordered pairs of non-statement-kind features co-occurring in one statement.
    Counts *combinations* of constructs, where many optimizer bugs live."""
    fs = sorted(f for f in features if not f.startswith("stmt:"))
    return {(a, b) for i, a in enumerate(fs) for b in fs[i + 1 :]}
