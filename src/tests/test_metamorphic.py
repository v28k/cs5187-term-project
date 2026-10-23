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
            assert c["rhs"] and (c["rhs"] != tc.statements[c["stmt"]] or c["kind"] == "cert")
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


def test_plan_shape_ignores_costs_and_relation_names():
    from pgfuzz.reference.pg_executor import plan_shape_string

    a = {"Node Type": "Hash Join", "Join Type": "Inner", "Parallel Aware": False, "Relation Name": "t0",
         "Plans": [{"Node Type": "Seq Scan", "Relation Name": "t0", "Parent Relationship": "Outer"},
                   {"Node Type": "Hash", "Parent Relationship": "Inner",
                    "Plans": [{"Node Type": "Seq Scan", "Relation Name": "t1", "Parent Relationship": "Outer"}]}]}
    b = {**a, "Relation Name": "t9", "Plans": [dict(a["Plans"][0], **{"Relation Name": "t3"}), a["Plans"][1]]}
    assert plan_shape_string(a) == plan_shape_string(b) == "Hash Join|Inner(Seq Scan|Outer,Hash|Inner(Seq Scan|Outer))"
    c = dict(a, **{"Join Type": "Left"})
    assert plan_shape_string(c) != plan_shape_string(a)


def test_tlp_having_keeps_the_level_grouped():
    # Without GROUP BY, HAVING makes a level a one-group aggregate (one row even if WHERE
    # removes every row), so the unpartitioned side must say HAVING TRUE, not drop HAVING.
    checks = _mini_checks("tlp_having")
    assert checks
    for sql, c in checks:
        head, _, pred = sql.partition(" HAVING ")
        assert c.lhs == head + " HAVING TRUE"
        assert f"HAVING NOT ({pred})" in c.rhs


def test_combinable_aggregate_items():
    from pgfuzz.grammar.rewrite import _combinable_items

    w = "MAX ( a1 . c0 ) AS c0 , COUNT ( * ) AS c1 , EVERY ( ( x ) ) AS c2".split()
    assert _combinable_items(w) == [("MAX", "c0"), ("SUM", "c1"), ("BOOL_AND", "c2")]
    assert _combinable_items("COUNT ( DISTINCT x ) AS c0".split()) is None          # not decomposable
    assert _combinable_items("MAX ( x ) + 1 AS c0".split()) is None                  # not one call
    assert _combinable_items("AVG ( x ) AS c0".split()) is None                      # AVG of AVGs is wrong
    assert _combinable_items("MAX ( x ) FILTER ( WHERE p ) AS c0".split()) is None


def test_new_rewrites_on_the_real_grammar():
    gen = GrammarGenerator(str(PGG), str(SCHEMA), mm_prob=1.0, mm_per_query=2,
                           mm_weights={"pred": 3, "notnull": 3, "order_drop": 1})
    gen.setup(GeneratorContext(5, random.Random(5), Path(tempfile.mkdtemp())))
    seen = Counter()
    for _ in range(1500):
        for c in gen.next_testcase().meta.get("checks", []):
            k, rhs = c["kind"], c["rhs"]
            seen[k] += 1
            if k == "pred:in_or":
                assert " OR " in rhs or rhs.count("=") >= 1
            elif k == "pred:cmp_negate":
                assert "(NOT (" in rhs.replace("( NOT (", "(NOT (")
            elif k == "notnull":
                assert "IS NOT NULL" in rhs
    for k in ("pred:in_or", "pred:cmp_negate", "pred:between", "notnull", "order_drop"):
        assert seen[k] > 0, (k, seen)

    agg = GrammarGenerator(str(PGG), str(SCHEMA), mm_prob=1.0, mm_weights={"tlp_agg": 1.0})
    agg.setup(GeneratorContext(5, random.Random(5), Path(tempfile.mkdtemp())))
    checks = [c for _ in range(1500) for c in agg.next_testcase().meta.get("checks", [])]
    assert checks
    for c in checks:
        assert c["kind"] == "tlp_agg" and c["lhs"] is not None
        assert "AS tlp_agg" in c["rhs"] and c["rhs"].count("UNION ALL") >= 2


def test_rls_and_cert_checks(tmp_path):
    from pgfuzz.grammar.rewrite import RLS_ROLE, load_policies

    pol = load_policies(str(SRC / "corpus" / "rls.sql"))
    assert pol["t0"] == "(c0 % 3) <> 0" and set(pol) == {"t0", "t1", "t3", "tp", "ti"}
    gen = GrammarGenerator(str(PGG), str(SCHEMA), mm_prob=1.0, mm_weights={"rls": 1.0, "cert": 1.0},
                           rls=str(SRC / "corpus" / "rls.sql"))
    gen.setup(GeneratorContext(4, random.Random(4), Path(tempfile.mkdtemp())))
    seen = Counter()
    for _ in range(400):
        tc = gen.next_testcase()
        for c in tc.meta.get("checks", []):
            seen[c["kind"]] += 1
            stmt = tc.statements[c["stmt"]]
            if c["kind"] == "rls":
                assert c["lhs"] == stmt and c["lhs_role"] == RLS_ROLE
                assert "(SELECT * FROM " in c["rhs"] and any(f"WHERE ({p})" in c["rhs"] for p in pol.values())
            else:
                assert c["kind"] == "cert" and c["rhs"] == stmt and len(c["lhs"]) < len(stmt)
    assert seen["rls"] and seen["cert"]


def test_cert_violation_is_a_performance_candidate():
    cls = oracle.classify(_result([{"kind": "cert", "status": "ok", "lhs_estimate": 10.0, "rhs_estimate": 25.0,
                                    "cert_violation": True, "lhs_sql": "a", "rhs_sql": "b"}]))
    assert cls.outcome is Outcome.PERFORMANCE and cls.details["oracle"] == "cert" and cls.is_bug_candidate
    ok = oracle.classify(_result([{"kind": "cert", "status": "ok", "lhs_estimate": 10.0, "rhs_estimate": 4.0}]))
    assert ok.outcome is Outcome.OK
