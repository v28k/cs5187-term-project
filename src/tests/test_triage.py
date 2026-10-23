import json

from pgfuzz.core.types import ExecResult, Outcome, StatementResult, StatementStatus as S
from pgfuzz.triage.precision import precision_table, render_markdown
from pgfuzz.triage.reduce import TokenReducer, fill, reduce_statements, split_pair
from pgfuzz.triage.sqltok import lex, render
from pgfuzz.triage.triage import load_candidate, same_failure, triage

TRAP = 'TRAP: failed Assert("list_length(x) == n"), File: "execExpr.c", Line: 2078, PID: 1'


class FakeServer:
    """Crashes with an assertion when a statement contains ROW(...) < ROW(...) inside JSON_TABLE."""

    def __init__(self):
        self.runs = 0

    def execute(self, tc):
        self.runs += 1
        out, log = [], []
        for sql in tc.statements:
            if "JSON_TABLE" in sql and "ROW" in sql and "<" in sql and sql.count("(") == sql.count(")"):
                out.append(StatementResult(S.CONNECTION_LOST, None, "server closed the connection unexpectedly"))
                log = [TRAP]
                break
            out.append(StatementResult(S.OK, rows=1))
        out += [StatementResult(S.SKIPPED) for _ in range(len(tc.statements) - len(out))]
        return ExecResult(out, server_log=log)

    def describe(self):
        return {"server_version": "fake"}


def _write_candidate(tmp_path, stmts, culprit, details, outcome="assertion"):
    (tmp_path / "tc1.sql").write_text(";\n".join(stmts) + ";\n")
    (tmp_path / "tc1.json").write_text(json.dumps({"outcome": outcome, "culprit": culprit, "details": details}))
    return tmp_path / "tc1.sql"


def test_triage_reproduces_and_reduces_an_assertion(tmp_path):
    stmts = ["CREATE INDEX ON t3 ((COALESCE (c1, c1)))",
             "SELECT a1.c0 FROM t0 AS a1 WHERE a1.c0 > 0",
             "SELECT DISTINCT ('NaN'::text || LEFT ('a'::text, 1)) AS c0, a1.c1 FROM t0 AS a1, JSON_TABLE ("
             "JSONB_BUILD_OBJECT ('k', CASE WHEN (ROW (1, 2) < ROW (3, 4)) THEN 'abc'::text ELSE 'x' END), '$[*]' "
             "COLUMNS (c0 int PATH '$.k')) AS a2 WHERE (a1.c0 = 1) ORDER BY 1"]
    details = {"assertion": {"expr": "list_length(x) == n", "file": "execExpr.c", "line": 2078}}
    cand = load_candidate(_write_candidate(tmp_path, stmts, 2, details))
    assert cand.oracle_name == "assertion"
    res = triage(cand, FakeServer(), tmp_path / "out", repeat=2, log=lambda s: None)
    assert res["reproduced"] == "2/2"
    assert res["reduced"]["statements"] == 1
    assert res["reduced"]["culprit_tokens"] < res["original"]["culprit_tokens"] // 2
    reduced = (tmp_path / "out" / "tc1" / "reduced.sql").read_text()
    assert "JSON_TABLE" in reduced and "ROW" in reduced
    assert (tmp_path / "out" / "tc1" / "report.md").exists()
    up = (tmp_path / "out" / "tc1" / "upstream_report.txt").read_text()
    assert 'TRAP: failed Assert("list_length(x) == n")' in up and "JSON_TABLE" in up and "Expected" in up


def test_same_failure_compares_assertions_and_variants(tmp_path):
    cand = load_candidate(_write_candidate(tmp_path, ["SELECT 1"], 0,
                                           {"assertion": {"expr": "a", "file": "f.c", "line": 1}}))
    from pgfuzz.eval.oracle import Classification
    same = Classification(Outcome.ASSERTION, [Outcome.ASSERTION], 0, details={"assertion": {"expr": "a", "file": "f.c"}})
    other = Classification(Outcome.ASSERTION, [Outcome.ASSERTION], 0, details={"assertion": {"expr": "b", "file": "f.c"}})
    assert same_failure(cand, same) and not same_failure(cand, other)


def test_paired_reduction_edits_both_sides_identically():
    a = "SELECT (COALESCE ('(,)'::int4range, '(,5]'::int4range) @> a4.c0) AS c0 FROM v0 AS a3 LEFT JOIN tl AS a4 ON (a3.c0 = a4.c0) WHERE TRUE"
    b = a.replace("COALESCE ('(,)'::int4range,", "COALESCE ((SELECT ('(,)'::int4range)),")
    skel, mid_a, mid_b = split_pair(a, b)
    assert render(fill(skel, mid_a)) == a and render(fill(skel, mid_b)) == b

    def interesting(toks):   # "bug" needs the LEFT JOIN and the containment test
        s = render(fill(toks, mid_a))
        return "LEFT JOIN" in s and "@>" in s and s.count("(") == s.count(")")

    red = TokenReducer(interesting).reduce(skel)
    ra, rb = render(fill(red, mid_a)), render(fill(red, mid_b))
    assert len(ra) < len(a) and "WHERE" not in ra
    assert ra.replace("'(,)'::int4range", "(SELECT ('(,)'::int4range))", 1) == rb  # still the same pair


def test_statement_ddmin_keeps_culprit_and_needed_setup():
    stmts = ["s0", "needed", "s2", "s3", "culprit", "s5"]
    def interesting(c, k):
        return c[k] == "culprit" and "needed" in c[:k]
    out, k = reduce_statements(stmts, 4, interesting)
    assert out == ["needed", "culprit"] and k == 1


def test_lexer_round_trip_and_no_glued_words():
    sql = "SELECT E'a\\'b', $$x;y$$, \"Q\"\"x\", 1.5e3, a1.c0::text FROM t -- c\nWHERE x >= -1"
    toks = lex(sql)
    assert render(toks).startswith("SELECT E'a\\'b', $$x;y$$")
    glued = toks[:1] + toks[3:]          # drop "E'a\\'b'" and ","
    assert render(glued).startswith("SELECT $$x;y$$")


def test_precision_table():
    rows = precision_table([
        {"oracle": "metamorphic:expr", "verdict": "real"},
        {"oracle": "metamorphic:expr", "verdict": "false_positive"},
        {"oracle": "assertion", "verdict": "real"},
        {"oracle": "assertion", "verdict": "duplicate"},
        {"oracle": "plan-variant", "verdict": "TODO"},
    ])
    by = {r["oracle"]: r for r in rows}
    assert by["metamorphic:expr"]["precision"] == 0.5
    assert by["assertion"]["precision"] == 1.0 and by["assertion"]["duplicate"] == 1
    assert by["plan-variant"]["precision"] is None
    assert by["all"]["candidates"] == 5 and by["all"]["precision"] == round(2 / 3, 3)
    assert "| assertion | 2 | 1 | 1 |" in render_markdown(rows)


def test_localization_verdicts():
    from pgfuzz.triage.localize import _verdict

    variants = {"no_hashagg": {"enable_hashagg": "off"}, "nestloop_only": {"enable_hashjoin": "off"}}
    d = {"lhs": {"hash": "a"}, "rhs": {"hash": "b"}}
    # the sides agree only without hash aggregation: a planner path, named with its source files
    v = _verdict(["lhs", "rhs"], d, None, {"no_hashagg": {"sides_agree": True}, "nestloop_only": {"sides_agree": False}},
                 variants)
    assert v["kind"] == "planner" and v["settings"] == ["enable_hashagg"] and "nodeAgg.c" in v["suspects"]["enable_hashagg"]
    v = _verdict(["lhs", "rhs"], d, None, {"no_hashagg": {"sides_agree": False}}, variants)
    assert v["kind"] == "not_toggled_by_planner_settings"
    v = _verdict(["query"], {"query": {"hash": "a"}}, {"hash": "b"},
                 {"no_hashagg": {"changes_answer": True, "agrees_with_release": True}}, variants)
    assert v["kind"] == "planner" and v["variants"] == ["no_hashagg"]
