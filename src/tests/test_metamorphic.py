import random
import tempfile
from collections import Counter
from pathlib import Path

from pgfuzz.core.interfaces import GeneratorContext
from pgfuzz.core.types import ExecResult, Outcome, StatementResult, StatementStatus as S, TestCase
from pgfuzz.eval import oracle, signature
from pgfuzz.eval.differential import eligible
from pgfuzz.grammar import Engine, load_grammar, parse_grammar, render
from pgfuzz.grammar.generator import GrammarGenerator
from pgfuzz.grammar.rewrite import Rewriter, expr_rewrites
from pgfuzz.grammar.schema import schema_from_dict

SRC = Path(__file__).resolve().parents[1]
PGG = SRC / "grammar" / "postgres.pgg"
SCHEMA = SRC / "corpus" / "schema.yaml"

# A tiny grammar with the rule names the rewriter looks for.
MINI = """
%type int  "int"  num key
%type bool "boolean" key
%start stmt

stmt : query ;
query @scope : select_core ;
select_core
  : SELECT @items ^from_clause ^where_clause
  | SELECT @items ^from_clause GROUP BY ^@group_keys having_clause
  ;
from_clause : FROM @table ;
where_clause : WHERE expr<bool> ;
having_clause @set(agg_ok) : HAVING expr<bool> ;
select_item<T> : expr<T> ;
expr<T> : <5> @col(T) | @lit(T) ;
expr<bool> : "(" expr<int> ">" expr<int> ")" ;
"""
MINI_SCHEMA = schema_from_dict({"relations": {"t": {"columns": [["a", "int"], ["b", "int"]]}}})


def _mini_checks(kind, seed=1, n=40):
    g = parse_grammar(MINI)
    eng = Engine(g, MINI_SCHEMA, random.Random(seed))
    rw = Rewriter(g, random.Random(seed), per_query=1, weights={kind: 1.0})
    out = []
    for _ in range(n):
        eng.new_testcase()
        tree, toks = eng.statement()
        sql = render(toks)
        out += [(sql, c) for c in rw.checks(0, tree, toks, sql, MINI_SCHEMA)]
    return out


def test_tlp_where_partitions_the_where_predicate():
    checks = _mini_checks("tlp_where")
    assert checks
    for sql, c in checks:
        head, _, pred = sql.partition(" WHERE ")
        assert c.lhs == head
        assert c.rhs == (f"(SELECT{head[6:]} WHERE ({pred})) UNION ALL (SELECT{head[6:]} WHERE NOT ({pred}))"
                         f" UNION ALL (SELECT{head[6:]} WHERE ({pred}) IS NULL)")


def test_norec_counts_with_and_without_the_predicate():
    for sql, c in _mini_checks("norec"):
        _, _, rest = sql.partition(" FROM ")
        frm, _, pred = rest.partition(" WHERE ")
        assert c.lhs == f"SELECT COUNT (*) FROM {frm} WHERE {pred}"
        assert c.rhs == f"SELECT COALESCE (SUM (CASE WHEN ({pred}) THEN 1 ELSE 0 END), 0) FROM {frm}"


def test_expression_rewrites_change_exactly_one_node():
    checks = _mini_checks("expr", n=60)
    assert checks
    for sql, c in checks:
        assert c.lhs is None and c.rhs != sql and c.kind.startswith("expr:")
        name = c.kind.split(":")[1]
        assert any(name in expr_rewrites(t) for t in ("int", "bool"))


def test_table_fence_wraps_one_table():
    for sql, c in _mini_checks("table_fence"):
        assert c.rhs == sql.replace("FROM t AS a1", "FROM (SELECT * FROM t OFFSET 0) AS a1", 1)


def test_generator_attaches_eligible_checks_on_the_real_grammar():
    gen = GrammarGenerator(str(PGG), str(SCHEMA), mm_prob=1.0, mm_per_query=2)
    gen.setup(GeneratorContext(3, random.Random(3), Path(tempfile.mkdtemp())))
    kinds = Counter()
    for _ in range(250):
        tc = gen.next_testcase()
        for c in tc.meta.get("checks", []):
            assert 0 <= c["stmt"] < len(tc.statements)
            assert eligible(tc.statements[c["stmt"]])
            assert c["rhs"] and c["rhs"] != tc.statements[c["stmt"]]
            kinds[c["kind"].split(":")[0]] += 1
    assert {"tlp_where", "norec", "expr", "table_fence"} <= set(kinds)
    assert gen.stats()["metamorphic_checks_built"] == dict(kinds)


def _result(checks):
    return ExecResult([StatementResult(S.OK, rows=3, checks=checks)])


def test_confirmed_mismatch_is_a_wrong_result():
    cls = oracle.classify(_result([{"kind": "tlp_where", "status": "ok", "lhs_hash": "a", "rhs_hash": "b",
                                    "lhs_rows": 3, "rhs_rows": 2, "confirmed": True,
                                    "lhs_sql": "SELECT 1", "rhs_sql": "SELECT 2"}]))
    assert cls.outcome is Outcome.WRONG_RESULT
    assert cls.details["variant"] == "mm:tlp_where" and cls.details["oracle"] == "metamorphic"
    tc = TestCase(["SELECT a1.c0 FROM t0 AS a1 WHERE a1.c0 > 0"])
    assert "mm:tlp_where" in signature.compute(cls, tc).key


def test_unconfirmed_mismatch_and_ordinary_errors_are_not_bugs():
    flaky = {"kind": "norec", "status": "ok", "lhs_hash": "a", "rhs_hash": "b", "confirmed": False}
    div0 = {"kind": "expr:scalar_sub", "status": "error", "sqlstate": "22012", "message": "division by zero", "side": "rhs"}
    assert oracle.classify(_result([flaky, div0])).outcome is Outcome.OK


def test_internal_error_in_a_followup_is_a_candidate():
    xx = {"kind": "cte_materialize", "status": "error", "sqlstate": "XX000",
          "message": "variable not found in subplan target list", "side": "rhs", "sql": "WITH ..."}
    cls = oracle.classify(_result([xx]))
    assert cls.outcome is Outcome.INTERNAL_ERROR and cls.details["check"] == "cte_materialize"
