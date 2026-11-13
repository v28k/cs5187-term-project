"""D4: precision ledger from bug-hunt documents."""

from pgfuzz.triage.ledger import build, render


def test_ledger(tmp_path):
    d = tmp_path / "duckdb"
    (d / "D-01-x").mkdir(parents=True)
    (d / "candidates.md").write_text("| Signature | Oracle | Verdict | Notes |\n|---|---|---|---|\n"
                                     "| 2a6e4c3ebd4a | internal error | **real, D-01** | x |\n"
                                     "| 8a79e28804df | cross-version | false positive (harness) | y |\n"
                                     "| 8a79e28804dd | cross-version | duplicate of 8a79 | y |\n")
    (d / "D-01-x" / "report.md").write_text("# D-01: thing\n\n| | |\n|---|---|\n| Status | **ready** |\n")
    (tmp_path / "filed.yaml").write_text("D-01-x:\n  issue: https://example.org/1\n")
    led = build(tmp_path)
    rows = {(r["engine"], r["oracle"]): r for r in led["rows"]}
    assert rows[("duckdb", "internal error")]["precision"] == 1.0
    assert rows[("duckdb", "cross-version")]["false_positive"] == 1
    assert rows[("duckdb", "cross-version")]["duplicate"] == 1
    assert led["packages"][0]["status"].startswith("filed: [issue](https://example.org/1)")
    assert "| duckdb | internal error | 1 | 0 |" in render(led)
