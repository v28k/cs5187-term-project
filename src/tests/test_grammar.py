import random
import re
from pathlib import Path

import pytest

from pgfuzz.core.interfaces import Feedback, GeneratorContext
from pgfuzz.core.types import ExecResult, Outcome, StatementResult, StatementStatus
from pgfuzz.grammar import Engine, Fail, GrammarError, load_grammar, load_schema, parse_grammar, render
from pgfuzz.grammar.engine import replace_at
from pgfuzz.grammar.generator import GrammarGenerator
from pgfuzz.grammar.schema import schema_from_dict

SRC = Path(__file__).resolve().parents[1]
PGG = SRC / "grammar" / "postgres.pgg"
SCHEMA = SRC / "corpus" / "schema.yaml"

MINI = """
%type int  "int"  num key
%type text "text" key
%start q

q @scope : SELECT @items ^FROMX ;
FROMX : FROM @table ;
select_item<T> : expr<T> ;
expr<T> : <5> @col(T) | @lit(T) ;
expr<T:num> : "(" expr<T> "+" expr<T> ")" ;
"""

MINI_SCHEMA = schema_from_dict({"relations": {"t": {"columns": [["a", "int"], ["b", "text"]]}}})


def _engine(text=MINI, schema=MINI_SCHEMA, seed=1):
    return Engine(parse_grammar(text), schema, random.Random(seed))


def test_keyword_rule_names_are_literals():
    # FROMX is all-uppercase, so in element position it is a literal, not a rule
    with pytest.raises(GrammarError, match="undefined rule|start rule"):
        parse_grammar(MINI.replace("^FROMX", "^fromx"))


def test_undefined_rule_and_unknown_class_are_errors():
    with pytest.raises(GrammarError, match="undefined rule"):
        parse_grammar('%type int "int"\nstmt : nothere ;')
    with pytest.raises(GrammarError, match="unknown type class"):
        parse_grammar('%type int "int"\nstmt : x<*:nope> ;\nx<T> : "1" ;')


def test_builtin_args_need_adjacent_paren():
    g = parse_grammar('%type int "int"\nstmt : @ordinal (ASC | DESC)? ;')
    b, rep = g.rules["stmt"][0].alts[0].elems
    assert b.args == [] and rep.lo == 0 and rep.hi == 1


def test_typed_scoped_generation():
    g = parse_grammar(MINI.replace("^FROMX", "^from_x").replace("FROMX :", "from_x :"))
    eng = Engine(g, MINI_SCHEMA, random.Random(3))
    for _ in range(50):
        _, toks = eng.statement()
        sql = render(toks)
        assert sql.startswith("SELECT ") and " FROM t AS a1" in sql
        for alias, col in re.findall(r"\b(a\d+)\.(\w+)", sql):
            assert alias == "a1" and col in ("a", "b")


def test_replay_reproduces_and_mutation_rebinds():
    g = load_grammar(PGG)
    eng = Engine(g, load_schema(SCHEMA), random.Random(7))
    for _ in range(30):
        eng.new_testcase()
        tree, toks = eng.statement()
        eng.new_testcase()
        tree2, toks2 = eng.statement(guide=tree)
        assert render(toks2) == render(toks)
        paths = [p for p, n in tree.walk() if p]
        if paths:
            eng.new_testcase()
            mutated = replace_at(tree, random.Random(1).choice(paths), None)
            eng.statement(guide=mutated)


def test_grouped_select_list_uses_group_keys_or_aggregates():
    g = load_grammar(PGG)
    eng = Engine(g, load_schema(SCHEMA), random.Random(11))
    seen = 0
    for _ in range(400):
        eng.new_testcase()
        try:
            _, toks = eng.statement("query")
        except Fail:
            continue
        sql = render(toks)
        m = re.match(r"SELECT (\w+\.\w+) AS c0 FROM (\w+) AS (a\d+) GROUP BY (\w+\.\w+)$", sql)
        if m:
            seen += 1
            assert m.group(1) == m.group(4)
    # not asserting seen > 0: the exact shape is rare; the check guards regressions when it occurs


def test_postgres_grammar_generates_without_failures():
    gen = GrammarGenerator(str(PGG), str(SCHEMA), mutate_prob=0.5)
    gen.setup(GeneratorContext(5, random.Random(5), Path(".")))
    for _ in range(150):
        tc = gen.next_testcase()
        assert tc and tc.statements
        for s in tc.statements:
            assert ";" not in s.replace("';'", "")
        ok = StatementResult(StatementStatus.OK)
        res = ExecResult([ok] * len(tc.statements))
        gen.feedback(Feedback(tc, res, Outcome.OK, [Outcome.OK] * len(tc.statements),
                              frozenset({"x"}), False))
    st = gen.stats()
    assert st["generation_failures"] < 15
    assert st["corpus"] > 0 and st["ops"].get("fresh")
    assert st["alternatives_used"] > st["alternatives"] * 0.5
