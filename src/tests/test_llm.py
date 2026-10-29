import json
import subprocess
from pathlib import Path

import pytest

from pgfuzz.core.types import ExecResult, StatementResult, StatementStatus as S
from pgfuzz.llm import commits as cm
from pgfuzz.llm.client import LLMClient, NeedsManualResponse, cost
from pgfuzz.llm.diffcov import map_lines
from pgfuzz.llm.gate import Gate, GateConfig
from pgfuzz.llm.loop import extend, summarize
from pgfuzz.llm.prompt import commit_message, feedback_message, system_prompt

SRC = Path(__file__).resolve().parents[1]
GRAMMAR, SCHEMA = SRC / "grammar" / "postgres.pgg", SRC / "corpus" / "schema.yaml"

GOOD = 'expr<bool> : <1> "(" "num_nonnulls" "(" expr<int> "," expr<text> ")" ">" "0" ")" ;'
BAD_SQL = 'expr<bool> : <1> "(" "no_such_function" "(" expr<int> ")" ")" ;'


class FakeServer:
    """Accepts everything except statements calling no_such_function."""

    def __init__(self):
        self.runs = 0

    def execute(self, tc):
        self.runs += 1
        out = []
        for sql in tc.statements:
            if "no_such_function" in sql:
                out.append(StatementResult(S.ERROR, "42883", "function no_such_function(integer) does not exist"))
            else:
                out.append(StatementResult(S.OK, rows=1))
        return ExecResult(out)


def _commit():
    return cm.CommitDigest("abcdef0123456789", "2026-10-01", "Fix num_nonnulls with mixed arguments", "body",
                           ["src/backend/utils/adt/misc.c"], ["pg_num_nonnulls"],
                           {"src/backend/utils/adt/misc.c": [10, 11, 12]}, "SELECT num_nonnulls(1, 'a');",
                           {"target_lines": 3, "files": 1})


def _gate(**kw):
    return Gate(GRAMMAR, SCHEMA, FakeServer(), GateConfig(sample_n=60, **kw))


def test_gate_accepts_reachable_valid_fragment():
    rep = _gate().check(GOOD, ["SELECT num_nonnulls(1, NULL::text);"], _commit())
    assert rep.details["parse"] == "ok"
    assert rep.details["reachability"]["uses"] >= 5
    assert rep.details["validity"]["rate"] == 1.0
    assert rep.accepted and rep.accepted_fragment and len(rep.accepted_seeds) == 1
    assert rep.details["coverage"].startswith("not measured")


def test_gate_rejects_invalid_sql_and_bad_grammar():
    rep = _gate().check(BAD_SQL, ["SELECT no_such_function(1);", "SELECT 1"], _commit())
    assert not rep.accepted
    assert rep.details["validity"]["rate"] == 0.0
    assert any("does not exist" in k for k in rep.details["validity"]["top_errors"])
    assert rep.details["seeds"][0]["ok"] is False and rep.accepted_seeds == ["SELECT 1"]  # kept, fragment still rejected
    for frag in ['expr<bool> : "(" @nonsense(int) ")" ;', "%type foo \"foo\"\n", 'expr<bool> : "(" missing_rule ")" ;']:
        rep = _gate().check(frag, [], _commit())
        assert rep.details["parse"] != "ok" and not rep.accepted


def test_client_manual_mode_and_replay(tmp_path):
    c = LLMClient(tmp_path, mode="manual")
    with pytest.raises(NeedsManualResponse) as e:
        c.ask("k-r0", "SYSTEM", [{"role": "user", "content": "hello"}])
    prompt = Path(str(e.value)).read_text()
    assert "SYSTEM" in prompt and "hello" in prompt and '"grammar_fragment"' in prompt
    (tmp_path / "responses" / "k-r0.json").write_text(json.dumps({"rationale": "r", "grammar_fragment": GOOD,
                                                                  "seeds": ["SELECT 1", " "], "features": []}))
    r = c.ask("k-r0", "SYSTEM", [])
    assert r.cached and r.data["seeds"] == ["SELECT 1"] and r.data["grammar_fragment"] == GOOD
    assert cost("claude-opus-5-5", {"input_tokens": 1_000_000, "output_tokens": 100_000}) == 6.0


def test_loop_repairs_then_accepts_and_resumes(tmp_path):
    client = LLMClient(tmp_path, mode="manual")
    commit = _commit()
    resp = tmp_path / "responses"
    resp.mkdir(parents=True, exist_ok=True)
    (resp / f"{commit.short}-r0.json").write_text(json.dumps(
        {"rationale": "", "grammar_fragment": BAD_SQL, "seeds": [], "features": ["x"]}))
    system = system_prompt(GRAMMAR, SCHEMA)
    res = extend([commit], client, _gate(), system, tmp_path, max_rounds=3)
    assert res.stopped_for and res.stopped_for.endswith(f"{commit.short}-r1.md")
    prompt = Path(res.stopped_for).read_text()
    assert "did not pass the validation gate" in prompt and "does not exist" in prompt
    (resp / f"{commit.short}-r1.json").write_text(json.dumps(
        {"rationale": "", "grammar_fragment": GOOD, "seeds": ["SELECT num_nonnulls(1, 'a')"], "features": ["x"]}))
    res = extend([commit], client, _gate(), system, tmp_path, max_rounds=3)
    assert res.accepted == 1 and res.stopped_for is None
    assert (tmp_path / "fragments" / f"{commit.short}.pgg").exists()
    assert (tmp_path / "seeds" / f"{commit.short}-0.sql").exists()
    s = summarize(tmp_path)
    assert s["accepted"] == 1 and s["accepted_by_round"] == {2: 1} and s["rejections_by_stage"] == {"validity": 1}
    rows = (tmp_path / "ledger.jsonl").read_text().splitlines()
    res = extend([commit], client, _gate(), system, tmp_path, max_rounds=3)     # finished commits are skipped
    assert res.done == 0 and len((tmp_path / "ledger.jsonl").read_text().splitlines()) == len(rows)


def test_generator_loads_fragments_and_seeds(tmp_path):
    import random

    from pgfuzz.core.interfaces import GeneratorContext
    from pgfuzz.grammar.generator import GrammarGenerator

    (tmp_path / "good.pgg").write_text(GOOD)
    (tmp_path / "broken.pgg").write_text('expr<bool> : "(" undefined_rule ")" ;')
    (tmp_path / "s.sql").write_text("SELECT 1;\nSELECT 2;\n")
    gen = GrammarGenerator(str(GRAMMAR), str(SCHEMA), extra_grammars=[str(tmp_path)], seeds=str(tmp_path),
                           seed_prob=0.5)
    gen.setup(GeneratorContext(1, random.Random(1), tmp_path))
    assert gen.fragments_loaded == ["good.pgg"] and "broken.pgg" in gen.fragments_rejected
    ops = [gen.next_testcase().meta.get("op") for _ in range(30)]
    assert "seed" in ops
    assert gen.describe()["fragments"] == ["broken.pgg", "good.pgg"]


def test_prompts_and_commit_mining(tmp_path):
    msg = commit_message(_commit())
    assert "num_nonnulls" in msg and "misc.c: 3 changed lines" in msg
    assert "parse" in feedback_message({"parse": "line 1: unknown rule"})
    sp = system_prompt(GRAMMAR, SCHEMA)
    assert "expr<bool>" in sp and "@col(T)" in sp

    repo = tmp_path / "pg"
    adt = repo / "src" / "backend" / "utils" / "adt"
    sql = repo / "src" / "test" / "regress" / "sql"
    adt.mkdir(parents=True)
    sql.mkdir(parents=True)
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (adt / "f.c").write_text("int\nf(int x)\n{\n\treturn x;\n}\n")
    subprocess.run(git + ["add", "."], check=True)
    subprocess.run(git + ["commit", "-qm", "init"], check=True)
    (adt / "f.c").write_text("int\nf(int x)\n{\n\tif (x < 0)\n\t\treturn 0;\n\treturn x;\n}\n")
    (sql / "f.sql").write_text("SELECT f(-1);\n")
    subprocess.run(git + ["add", "."], check=True)
    subprocess.run(git + ["commit", "-qm", "Fix f for negative input"], check=True)
    (adt / "f.c").write_text("/* header */\nint\nf(int x)\n{\n\tif (x < 0)\n\t\treturn 0;\n\treturn x;\n}\n")
    subprocess.run(git + ["commit", "-qam", "Add header comment typo"], check=True)

    ds = cm.mine(repo, "HEAD~2", "HEAD~1")
    assert len(ds) == 1
    d = ds[0]
    assert d.subject == "Fix f for negative input" and d.regress_sql == "SELECT f(-1);"
    assert d.targets == {"src/backend/utils/adt/f.c": [4, 5]}
    cm.save(ds, tmp_path / "c.json")
    assert cm.load(tmp_path / "c.json")[0].targets == d.targets
    # the next commit inserted one line above: the targets move down by one
    assert map_lines(repo, d.sha, "HEAD", "src/backend/utils/adt/f.c", [4, 5]) == [5, 6]


def test_llm_rewrites_reach_the_metamorphic_oracle(tmp_path):
    import random

    from pgfuzz.core.interfaces import GeneratorContext
    from pgfuzz.grammar.generator import GrammarGenerator
    from pgfuzz.grammar.rewrite import template_rewrite

    assert template_rewrite("COALESCE({e}, {e})")(["x"]) == ["(", "COALESCE(", "(", "x", ")", ",", "(", "x", ")", ")", ")"]
    (tmp_path / "rw.json").write_text(json.dumps({"rewrites": [
        {"name": "null_case", "type": "int", "template": "CASE WHEN {e} IS NULL THEN NULL ELSE {e} END"},
        {"name": "bad", "type": "nope", "template": "{e}"}]}))
    gen = GrammarGenerator(str(GRAMMAR), str(SCHEMA), mm_prob=1.0, mm_weights={"expr": 1.0},
                           extra_rewrites=str(tmp_path), only_rewrite="llm_null_case")
    gen.setup(GeneratorContext(2, random.Random(2), tmp_path))
    checks = [c for _ in range(200) for c in gen.next_testcase().meta.get("checks", [])]
    assert checks and all(c["kind"] == "expr:llm_null_case" and "CASE WHEN" in c["rhs"] for c in checks)
    assert gen.stats()["llm_rewrites"] == 1          # the unknown type was dropped


def test_client_keeps_rewrites(tmp_path):
    c = LLMClient(tmp_path, mode="manual")
    (tmp_path / "responses" / "k.json").write_text(json.dumps({"rationale": "", "grammar_fragment": "", "seeds": [],
        "features": [], "rewrites": [{"name": "n", "type": "int", "template": "{e}", "why": ""}, {"name": "x"}]}))
    assert len(c.ask("k", "S", []).data["rewrites"]) == 1


def test_gate_rejects_a_rewrite_that_changes_the_collation():
    # The RQ3 campaign's one LLM false positive: NULLIF({e}, NULL::text COLLATE "POSIX") passed the value
    # probe and 150 sampled checks, but UPPER('e-acute') differs under another collation.
    from types import SimpleNamespace

    from pgfuzz.llm.gate import Gate, GateConfig

    g = object.__new__(Gate)
    g.grammar_path, g.cfg = str(GRAMMAR), GateConfig()
    g.ex = SimpleNamespace(mm_enabled=False, mm_confirm=False)
    accepted, info = g.check_rewrites([{"name": "posix", "type": "text", "template": 'NULLIF({e}, NULL::text COLLATE "POSIX")'}])
    assert not accepted and not info[0]["accepted"] and "COLLATE" in info[0]["reason"]
