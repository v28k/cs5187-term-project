import pytest

from pgfuzz.grammar.dsl import GrammarError, parse_grammar
from pgfuzz.grammar.overlay import apply_overlays

BASE = """
%type int "int" num
%type text "text"
%type rng "int4range"
%start stmt
stmt : SELECT expr<int> | SELECT expr<text> | <2> SELECT special ;
expr<T> : @lit(T) | "(" expr<T> ")" ;
expr<int> : expr<int> ( "+" | "-" | "?" ) expr<int> | LENGTH "(" expr<text> ")" ;
expr<bool> : expr<rng> "@>" expr<int> ;
expr<rng> : @lit(rng) ;
special : JSONB_THING "(" ")" ;
"""


def alts(text, rule):
    g = parse_grammar(text)
    return sum(len(v.alts) for v in g.rules.get(rule, []))


def test_drop_top_level_alternative():
    text, rep = apply_overlays(BASE, ['%drop stmt "special"'])
    assert alts(text, "stmt") == 2
    # special is now unused but still defined: no cascade needed
    assert rep.dropped and not rep.unmatched


def test_dropopt_inside_group():
    text, _ = apply_overlays(BASE, ['%dropopt expr "\\"?\\""'])
    assert '"?"' not in text
    assert '"+" | "-"' in text
    parse_grammar(text)


def test_droprule_cascades_to_users():
    text, rep = apply_overlays(BASE, ["%droprule special"])
    assert "special" not in parse_grammar(text).rules
    assert alts(text, "stmt") == 2
    assert any("needs special" in c for c in rep.cascaded)


def test_droptype_removes_variants_and_references():
    text, rep = apply_overlays(BASE, ["%droptype rng"])
    g = parse_grammar(text)
    assert "rng" not in g.types
    assert all(v.concrete != "rng" for v in g.rules["expr"])
    assert "@>" not in text


def test_replace_and_added_rules():
    ov = '%replace special "JSONB_THING" "JSON_THING"\nspecial : OTHER "(" ")" ;\n'
    text, rep = apply_overlays(BASE, [ov])
    g = parse_grammar(text)
    assert alts(text, "special") == 2 and "JSONB_THING" not in text
    assert rep.added_lines == 1 and rep.replaced


def test_weight():
    text, _ = apply_overlays(BASE, ['%weight stmt "expr<text>" 7'])
    g = parse_grammar(text)
    w = [a.weight for v in g.rules["stmt"] for a in v.alts]
    assert 7.0 in w and 2.0 in w


def test_group_emptied_removes_enclosing_alternative():
    base = BASE.replace('( "+" | "-" | "?" )', '( "?" )')
    text, rep = apply_overlays(base, ['%dropopt expr "\\"?\\""'])
    assert "LENGTH" in text and '"?"' not in text
    assert any("group emptied" in d for d in rep.dropped)


def test_unmatched_is_reported():
    _, rep = apply_overlays(BASE, ['%drop stmt "NO_SUCH_THING"'])
    assert rep.unmatched == ['%drop stmt NO_SUCH_THING']


def test_unknown_directive():
    with pytest.raises(GrammarError):
        apply_overlays(BASE, ["%frobnicate x"])
