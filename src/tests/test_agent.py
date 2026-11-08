"""Autonomous agent pieces (D1, D3): native regression tests, package drafts, hunt helpers."""

import json
from pathlib import Path

import yaml

from pgfuzz.agent.hunt import _engine, _tmp_config, new_failures
from pgfuzz.agent.nativetest import native_test
from pgfuzz.agent.package import make_package
from pgfuzz.cli import main


def test_duckdb_test_format():
    t = native_test("duckdb", "x", ["CREATE TABLE t(a INT)"], "SELECT a, 'b' FROM t;", rows=[[1, "b"], [None, "c"]],
                    description="d")
    assert t.startswith("# name: test/sql/fuzzer/x.test")
    assert "statement ok\nCREATE TABLE t(a INT);" in t
    assert "query IT rowsort\nSELECT a, 'b' FROM t;\n----\n1\tb\nNULL\tc" in t


def test_slt_error_and_ok():
    t = native_test("datafusion", "x", [], "SELECT 1/0", error="Divide by zero")
    assert "statement error\nSELECT 1/0;\n----\nDivide by zero" in t
    t = native_test("sqlite", "x", [], "SELECT 1")
    assert "statement ok\nSELECT 1;" in t


def test_turso_format():
    t = native_test("turso", "x", ["CREATE TABLE t(a)"], "SELECT 1, 2", rows=[[1, 2]])
    assert "test x {\n    CREATE TABLE t(a);\n    SELECT 1, 2;\n}\nexpect {\n    1|2\n}" in t
    assert "expect error" in native_test("turso", "x", [], "SELECT x", error="no such column")


class _Ex:
    def run_rows(self, setup, query, limit=50):
        return {"rows": [[7]]}


def test_make_package(tmp_path):
    tri = tmp_path / "tri"
    tri.mkdir()
    (tri / "triage.json").write_text(json.dumps({"signature": "abc", "outcome": "wrong_result", "oracle": "tlp",
                                                 "reproduced": "3/3"}))
    (tri / "reduced.sql").write_text("-- c\nCREATE TABLE t(a INT);\nSELECT a FROM t;\n")
    out = make_package("duckdb", tri, tmp_path / "pk", executor=_Ex())
    assert out.name == "DUCKDB-abc"
    test = (out / "regression.test").read_text()
    assert "VERIFY" in test and "query I rowsort\nSELECT a FROM t;\n----\n7" in test
    for f in ("repro.sql", "report.md", "issue.md"):
        assert (out / f).exists()


def test_package_internal_error_cli(tmp_path, capsys):
    tri = tmp_path / "tri"
    tri.mkdir()
    (tri / "triage.json").write_text(json.dumps({"signature": "s1", "outcome": "internal_error"}))
    (tri / "reduced.sql").write_text("SELECT 1;\n")
    assert main(["-q", "package", "datafusion", str(tri), "--out", str(tmp_path / "pk")]) == 0
    assert "statement ok\nSELECT 1;" in (tmp_path / "pk" / "DATAFUSION-s1" / "regression.slt").read_text()


def test_hunt_helpers(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.safe_dump({"experiment": "e", "executor": {"kind": "datafusion"}, "budget": {"seconds": 9}}))
    tmp, raw = _tmp_config(cfg, 5, tmp_path / "out")
    assert raw["budget"] == {"seconds": 5} and raw["experiment"] == "hunt_e" and raw["trials"] == 1
    assert yaml.safe_load(tmp.read_text())["output_dir"] == str((tmp_path / "out").resolve())
    assert _engine(raw) == "datafusion" and _engine({"executor": {"dsn": "x"}}) == "postgres"
    for i, kb in enumerate([[], ["K1"]]):
        d = tmp_path / "exp" / "arm" / "trial-1" / "failures" / str(i)
        d.mkdir(parents=True)
        (d / "failure.json").write_text(json.dumps({"known_bugs": kb}))
    assert [p.name for p in new_failures(tmp_path / "exp")] == ["0"]
