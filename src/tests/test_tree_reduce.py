import json
import random
import tempfile
from pathlib import Path

from pgfuzz.core.interfaces import GeneratorContext
from pgfuzz.grammar.engine import MINIMAL, minimal_marker
from pgfuzz.grammar.generator import GrammarGenerator
from pgfuzz.grammar.treeio import from_json, to_json
from pgfuzz.triage.tree_reduce import TreeReducer, load_trees, size

SRC = Path(__file__).resolve().parents[1]
PGG, SCHEMA = SRC / "grammar" / "postgres.pgg", SRC / "corpus" / "schema.yaml"


def _gen(seed=1):
    g = GrammarGenerator(str(PGG), str(SCHEMA), mutate_prob=0.0)
    g.setup(GeneratorContext(seed, random.Random(seed), Path(tempfile.mkdtemp())))
    return g


def _failing_case(g, needle):
    for _ in range(3000):
        tc = g.next_testcase()
        if any(needle in s for s in tc.statements) and len(tc.statements) >= 2:
            return tc, g.failure_meta(tc)
    raise AssertionError("no test case with " + needle)


def test_tree_json_round_trip_replays_identically():
    g = _gen(3)
    tc, meta = _failing_case(g, "SELECT")
    meta = json.loads(json.dumps(meta))                     # as stored in failure.json
    other = _gen(9)                                          # a new grammar load: other uids, other rng
    replay = other._derive(load_trees(meta, other), strict=True)
    assert replay.sql == tc.statements
    m = other.alt_map()
    assert to_json(from_json(meta["trees"][0]["tree"], m), m) == meta["trees"][0]["tree"]


def test_minimal_marker_derives_a_smaller_valid_subtree():
    g = _gen(4)
    tc, meta = _failing_case(g, "WHERE")
    trees = load_trees(meta, g)
    root = trees[-1].tree
    big = max((n for p, n in root.walk() if p and n.sym == "expr"), key=lambda n: n.size(), default=None)
    assert big is not None
    marked = minimal_marker(big)
    assert marked.val == MINIMAL and marked.sym == "expr"


def test_tree_reduction_keeps_the_failure_and_shrinks_a_lot():
    g = _gen(5)
    tc, meta = _failing_case(g, "JSON_TABLE")
    calls = []

    def interesting(sql):
        calls.append(sql)
        return any("JSON_TABLE" in s for s in sql)

    other = _gen(6)
    red = TreeReducer(other, interesting, budget=300, log=lambda m: None)
    stmts, sql = red.reduce(load_trees(json.loads(json.dumps(meta)), other))
    assert any("JSON_TABLE" in s for s in sql)
    assert size(sql) < size(tc.statements) / 2, (size(sql), size(tc.statements))
    assert len(sql) == 1                                    # the setup statements were not needed
