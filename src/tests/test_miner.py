"""Overlay miner (A3): failing alternatives become %drop lines that the overlay engine accepts."""

from collections import Counter
from types import SimpleNamespace

from pgfuzz.grammar.dsl import parse_grammar
from pgfuzz.grammar.miner import mine, render_overlay
from pgfuzz.grammar.overlay import apply_overlays

G = '''%type int "int" num
%start stmt
stmt : SELECT e<int> ;
e<int> : <1> "1"
       | <1> ABS "(" e<int> ")"
       | <1> WIDTH_BUCKET "(" e<int> ")"
       ;
'''


def _gen(ok):
    g = parse_grammar(G)
    alts = {a.line: a for v in g.rules["e"] for a in v.alts}
    use, good = Counter(), Counter()
    for line, rate in ok.items():
        use[alts[line].uid] = 100
        good[alts[line].uid] = int(rate * 100)
    for v in g.rules["stmt"]:
        for a in v.alts:
            use[a.uid] = 100
    return SimpleNamespace(grammar=g, grammar_text=G, alt_use=use, alt_ok=good)


def test_mine_and_apply():
    found = mine(_gen({4: 1.0, 5: 0.9, 6: 0.0}))
    assert [(d["rule"], d["key"]) for d in found] == [("e", "<1> WIDTH_BUCKET")]
    ov = render_overlay(found, "x")
    text, rep = apply_overlays(G, [ov])
    assert rep.dropped and not rep.unmatched
    left = [a.span for v in parse_grammar(text).rules["e"] for a in v.alts]
    assert len(left) == 2 and all("WIDTH_BUCKET" not in text[a:b] for a, b in left)


def test_rule_with_all_failing_alternatives_is_not_blamed():
    assert mine(_gen({4: 0.0, 5: 0.0, 6: 0.0})) == []
