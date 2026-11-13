"""C6: test-suite import into seed files."""

from pgfuzz.agent.suites import import_suite, parse_slt, parse_sqltest
from pgfuzz.grammar.generator import parse_seed

SLT = """# name: test/x.test
# group: [x]

statement ok
CREATE TABLE t(a INT);

statement error
SELECT * FROM nope;
----
Catalog Error

onlyif postgres
query I
SELECT 99;
----
99

query II rowsort
SELECT a,
       a + 1 FROM t
----
1	2

statement ok
INSERT INTO t VALUES (1)
"""


def test_parse_slt():
    assert parse_slt(SLT) == ["CREATE TABLE t(a INT)", "SELECT a,\n       a + 1 FROM t", "INSERT INTO t VALUES (1)"]
    assert parse_slt("loop i 0 3\n\nstatement ok\nSELECT 1\n\nendloop\n") is None
    assert parse_slt("require parquet\n\nstatement ok\nSELECT 1\n") is None
    assert parse_slt("require vector_size 2\n\nstatement ok\nSELECT 1\n") == ["SELECT 1"]


def test_parse_sqltest():
    t = "@database :memory:\n\ntest a {\n    CREATE TABLE t(x);\n    SELECT 1;\n}\nexpect {\n    1\n}\n"
    assert parse_sqltest(t) == ["CREATE TABLE t(x)", "SELECT 1"]


def test_import_suite(tmp_path):
    d = tmp_path / "suite"
    d.mkdir()
    (d / "a.test").write_text(SLT)
    (d / "b.slt").write_text("loop i 0 2\n")
    st = import_suite([str(d)], tmp_path / "seeds")
    assert st == {"files": 2, "skipped_files": 1, "seeds": 1, "statements": 3}
    seed = next((tmp_path / "seeds").glob("*.sql")).read_text()
    stmts, _ = parse_seed(seed)
    assert len(stmts) == 3
