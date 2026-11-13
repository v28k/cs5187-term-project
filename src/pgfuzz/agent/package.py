"""Filing-package drafts from triage output (D3).

For a triaged candidate directory (``reduced.sql``, ``triage.json``) this writes
``<out>/<ENGINE>-<signature>/`` with ``repro.sql``, a regression test in the engine's own
format, ``report.md`` (facts: oracle, reproduction rate, reduced test case, observed rows) and
``issue.md`` (a skeleton). Expected results that the tool cannot know for sure are marked
``VERIFY``: a person (or the cross-version / cross-engine reference) has to confirm them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pgfuzz.agent.nativetest import FORMATS, native_test
from pgfuzz.core.sqlsplit import split_statements


def _statements(reduced_sql: str) -> list[str]:
    lines = [ln for ln in reduced_sql.splitlines() if not ln.lstrip().startswith("--")]
    return split_statements("\n".join(lines))


def make_package(engine: str, triage_dir: str | Path, out_root: str | Path, executor: Any | None = None) -> Path:
    tdir = Path(triage_dir)
    info = json.loads((tdir / "triage.json").read_text(encoding="utf-8"))
    sig = info.get("signature", tdir.name)
    stmts = _statements((tdir / "reduced.sql").read_text(encoding="utf-8"))
    out = Path(out_root) / f"{engine.upper()}-{sig}"
    out.mkdir(parents=True, exist_ok=True)
    setup, query = (stmts[:-1], stmts[-1]) if stmts else ([], "SELECT 1")
    observed: dict[str, Any] = {}
    if executor is not None and hasattr(executor, "run_rows"):
        observed = executor.run_rows(setup, query, limit=50)
    outcome = info.get("outcome", "?")
    if outcome in ("internal_error", "crash", "assertion", "hang"):
        test = native_test(engine, f"fuzz_{sig}", setup, query, rows=None,
                           description=f"{outcome} found by the grammar fuzzer (signature {sig}); must run without error")
    else:
        rows = observed.get("rows") if observed and "error" not in observed else None
        test = native_test(engine, f"fuzz_{sig}", setup, query, rows=rows,
                           description=f"{outcome} ({info.get('oracle')}); VERIFY: expected rows below are the "
                                       f"observed ones, replace them with the correct result")
    (out / f"regression{FORMATS.get(engine, '.sql')}").write_text(test, encoding="utf-8")
    (out / "repro.sql").write_text(";\n".join(stmts) + ";\n", encoding="utf-8")
    obs = json.dumps(observed, indent=1, default=str)[:3000] if observed else "(not executed)"
    (out / "report.md").write_text(
        f"# {engine} candidate {sig}\n\n| | |\n|---|---|\n| Outcome | {outcome} |\n| Oracle | {info.get('oracle')} |\n"
        f"| Reproduced | {info.get('reproduced')} |\n| Verdict | {info.get('verdict')} |\n"
        f"| Triage | `{tdir}` |\n\n## Reduced test case\n\n```sql\n" + ";\n".join(stmts) + ";\n```\n\n"
        f"## Observed (this build)\n\n```\n{obs}\n```\n\n## To do before filing\n\n"
        "1. Confirm on the engine's newest development build.\n2. Decide the expected result (docs, standard, "
        "another engine) and fix the regression test where it says VERIFY.\n3. Search the tracker for duplicates.\n"
        "4. Root-cause and, if clear, write a fix.\n", encoding="utf-8")
    (out / "issue.md").write_text(
        f"**Title:** <one line: what fails>\n\n**What happens?**\n\n<one or two sentences>\n\n**To Reproduce**\n\n"
        "```sql\n" + ";\n".join(stmts) + ";\n```\n\n**Expected:** <correct result and why>\n\n"
        "**Version:** <engine version / commit>\n", encoding="utf-8")
    return out
