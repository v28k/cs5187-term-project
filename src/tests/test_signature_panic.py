from pgfuzz.core.types import Outcome
from pgfuzz.eval.oracle import Classification
from pgfuzz.eval.signature import compute


def _cls(msg):
    return Classification(outcome=Outcome.CRASH, culprit=0, sqlstate=None, message=msg, details={"connection_lost": True},
                          statement_outcomes=[Outcome.CRASH])


def test_rust_panics_deduplicate_by_location():
    a = compute(_cls("turso worker died (exit code -6)\npanicked at core/translate/window.rs:3564:22:\nunreachable: got DATETIME"))
    b = compute(_cls("turso worker died (exit code -6)\npanicked at core/translate/window.rs:3564:22:\nunreachable: got INSTR"))
    c = compute(_cls("turso worker died (exit code -6)\npanicked at core/vdbe/mod.rs:1487:32:\ncursor id 1 is None"))
    assert a.id == b.id and a.strength == "panic" and a.id != c.id
