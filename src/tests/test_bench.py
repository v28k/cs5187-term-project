import json
from pathlib import Path

from pgfuzz.bench import reinjected as rb
from pgfuzz.core.types import Outcome
from pgfuzz.eval.oracle import Classification
from pgfuzz.eval.known_bugs import KnownBugCatalog

BENCH = Path(__file__).resolve().parents[1] / "bench" / "reinjected"


def _obs(*stmts, outcome="ok", details=None):
    return {"outcome": outcome, "message": None, "details": details or {},
            "statements": [dict(zip(("status", "sqlstate", "message", "rows", "hash"), s)) for s in stmts]}


def test_symptom_classes():
    ok = ("ok", None, None, 2, "h1")
    assert rb.symptom(_obs(ok), _obs(ok)) == ("none", "")
    assert rb.symptom(_obs(ok), _obs(("ok", None, None, 3, "h2")))[0] == "wrong_result"
    assert rb.symptom(_obs(ok), _obs(("error", "XX000", "could not find pathkey item to sort", None, None)))[0] \
        == "internal_error"
    assert rb.symptom(_obs(("error", "2201E", "cannot take logarithm", None, None)), _obs(ok))[0] == "missing_error"
    crash = _obs(("connection_lost", None, None, None, None), outcome="assertion",
                 details={"assertion": {"file": "initsplan.c", "expr": "bms_is_member(x)"}})
    assert rb.symptom(_obs(ok), crash) == ("assertion", "initsplan.c: bms_is_member(x)")


def test_bench_files_are_consistent():
    bench = rb.load(BENCH / "bugs.yaml")
    assert len(bench.bugs) == len({b.id for b in bench.bugs}) >= 15
    for b in bench.bugs:
        assert b.poc.exists(), b.poc
        assert b.raw.get("match"), f"{b.id} has no match criteria"
    KnownBugCatalog.load(BENCH / "bugs.yaml")        # parses as a known-bug catalog


def test_offline_entries_never_match_online(tmp_path):
    (tmp_path / "k.yaml").write_text("bugs:\n  - id: w\n    match: {outcome: wrong_result, offline: true}\n"
                                     "  - id: e\n    match: {outcome: internal_error, message_regex: pathkey}\n")
    cat = KnownBugCatalog.load(tmp_path / "k.yaml")
    wr = Classification(Outcome.WRONG_RESULT, [], culprit=0, message="mismatch", details={"variant": "mm:tlp_where"})
    ie = Classification(Outcome.INTERNAL_ERROR, [], culprit=0, sqlstate="XX000",
                        message="could not find pathkey item to sort")
    assert cat.match(wr) == [] and cat.match(ie) == ["e"]


def test_detection_table(tmp_path):
    bench = rb.Bench(tmp_path, "base", [rb.Bug("a", "c1", "", tmp_path, "assertion"),
                                        rb.Bug("b", "c2", "", tmp_path, "wrong_result"),
                                        rb.Bug("n", "c3", "", tmp_path, "none")])
    att = [{"arm": "grammar", "trial": "trial-00", "first_t": 30.0, "bugs": ["a"], "how": "signature"},
           {"arm": "grammar", "trial": "trial-00", "first_t": 10.0, "bugs": ["a"], "how": "solo"},
           {"arm": "grammar", "trial": "trial-01", "first_t": 50.0, "bugs": ["a", "b"], "how": "solo"},
           {"arm": "random", "trial": "trial-00", "first_t": 5.0, "bugs": [], "how": "native"}]
    t = rb.detection_table(bench, att, ["random", "grammar"], 2)
    assert t["observable_bugs"] == 2 and t["found_by_arm"] == {"random": 0, "grammar": 2}
    a = next(r for r in t["bugs"] if r["id"] == "a")
    assert a["grammar"] == {"found": 2, "trials": 2, "median_t": 30.0}
    assert t["native_failures"] == 1
    md = rb.render_markdown(t, ["random", "grammar"])
    assert "| a | assertion | 0/2 | 2/2 (30s) |" in md


def test_failures_listing(tmp_path):
    d = tmp_path / "grammar" / "trial-00" / "failures" / "sig1"
    d.mkdir(parents=True)
    (d / "failure.json").write_text(json.dumps({"signature": "sig1", "outcome": "assertion", "first_t": 12.5}))
    fs = rb.failures(tmp_path)
    assert fs[0]["arm"] == "grammar" and fs[0]["trial"] == "trial-00" and fs[0]["first_t"] == 12.5
