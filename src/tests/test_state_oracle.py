"""State-restoration oracle: a rolled-back test case must leave the database unchanged."""

import pytest

from pgfuzz.core.types import TestCase
from pgfuzz.eval import oracle

SCHEMA = "CREATE TABLE t(a INTEGER PRIMARY KEY, b TEXT);\nINSERT INTO t VALUES (1, 'x');\n"


@pytest.fixture
def setup_file(tmp_path):
    p = tmp_path / "schema.sql"
    p.write_text(SCHEMA)
    return str(p)


def _run(ex, cases):
    ex.start()
    try:
        return [oracle.classify(ex.execute(TestCase(list(c), origin="test", id=i))) for i, c in enumerate(cases)]
    finally:
        ex.stop()


def test_sqlite_restores_state(setup_file):
    pytest.importorskip("apsw")
    from pgfuzz.targets.sqlite_executor import SQLiteExecutor

    ex = SQLiteExecutor(setup_sql=setup_file, rules=False, metamorphic=True)
    out = _run(ex, [["INSERT INTO t(b) VALUES ('w')"], ["SELECT abs(-9223372036854775808)", "INSERT INTO t(b) VALUES ('y')"],
                    ["INSERT INTO t(b) VALUES ('z')", "SELECT count(*) FROM t"]])
    assert not any(c.is_bug_candidate for c in out)
    assert ex.diff_stats.get("state_leaks", 0) == 0


def test_leak_is_reported_and_repaired(setup_file):
    """A driver whose ROLLBACK is lost after a failing statement (as pyturso 0.8.3 does)."""
    pytest.importorskip("apsw")
    from pgfuzz.targets.base import WorkerExecutor

    ex = WorkerExecutor(driver="tests.test_state_oracle:LeakyDriver", setup_sql=setup_file, metamorphic=True)
    out = _run(ex, [["INSERT INTO t(b) VALUES ('w')"],                       # first write: takes the baseline
                    ["SELECT abs(-9223372036854775808)", "INSERT INTO t(b) VALUES ('leak')"],
                    ["INSERT INTO t(b) VALUES ('later')", "SELECT count(*) FROM t"]])
    assert out[1].is_bug_candidate and "state_restore" in (out[1].message or "")
    assert not out[2].is_bug_candidate                                        # the worker was reset
    assert ex.diff_stats["state_leaks"] == 1


try:
    from pgfuzz.targets.sqlite_executor import SQLiteDriver

    class LeakyDriver(SQLiteDriver):
        def execute(self, sql, fetch, max_rows):
            try:
                return super().execute(sql, fetch, max_rows)
            except Exception:
                if not self.db.getautocommit():
                    self._run("COMMIT")          # the failing statement ends the transaction
                raise
except Exception:                                # apsw missing: the tests above are skipped
    pass


def test_localize_skips_non_postgres_executor():
    from pgfuzz.triage.localize import localize

    class Other:
        pass

    out = localize(Other(), [], {"q": "SELECT 1"})
    assert "skipped" in out


def test_known_bug_sql_regex_matches_culprit_statement(tmp_path):
    from types import SimpleNamespace

    from pgfuzz.eval.known_bugs import KnownBugCatalog
    from pgfuzz.eval.oracle import Classification, Outcome

    p = tmp_path / "kb.yaml"
    p.write_text(
        "bugs:\n"
        "  - id: b1\n"
        "    match:\n"
        "      outcome: wrong_result\n"
        "      sql_regex: '(?i)percentile_disc\\s*\\('\n"
    )
    cat = KnownBugCatalog.load(p)
    cls = Classification(Outcome.WRONG_RESULT, [], culprit=1)
    tc = SimpleNamespace(statements=["CREATE TABLE t(a INT)", "SELECT percentile_disc(a, 1) FROM t"])
    assert cat.match(cls, tc) == ["b1"]
    tc.statements[1] = "SELECT max(a) FROM t"
    assert cat.match(cls, tc) == []
    assert cat.match(cls) == []          # no SQL: an sql_regex entry cannot match
