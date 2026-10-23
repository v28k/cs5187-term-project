"""Prompts for the commit-directed grammar extension (Grammar + LLM arm).

The model reads one PostgreSQL commit and answers with (a) a ``.pgg`` grammar
fragment that makes the grammar generator produce SQL reaching the changed
code, and (b) a few seed test cases. It never writes the thousands of test
cases a campaign runs; the grammar does. The system prompt is the same for
every commit (DSL reference, builtins, conventions, schema, the current
grammar), so it is cached and only the commit digest and feedback vary.
"""

from __future__ import annotations

import json
from pathlib import Path

from pgfuzz.grammar import dsl
from pgfuzz.llm.commits import CommitDigest

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "rationale": {"type": "string",
                      "description": "Which code paths the commit changed and which SQL reaches them (3-6 sentences)."},
        "grammar_fragment": {"type": "string",
                             "description": ".pgg text: new alternatives (as new variants of existing rules) and new rules. "
                                            "Empty string if the existing grammar already covers the commit."},
        "seeds": {"type": "array", "items": {"type": "string"},
                  "description": "1-5 test cases; each is one or more SQL statements separated by ';' and newlines."},
        "features": {"type": "array", "items": {"type": "string"},
                     "description": "Short names of the SQL features the fragment targets."},
    },
    "required": ["rationale", "grammar_fragment", "seeds", "features"],
    "additionalProperties": False,
}

BUILTINS = """\
@col(T)            a visible column of type T, rendered qualified (a1.c0)
@lit(T)            a literal of type T
@table / @table(plain) / @table(t1)   a relation from the schema (or one named), bound to a fresh alias "AS aN"
@items / @items(rule, nowin)           the select list: one select_item<T> per type of the current shape, "AS c0, c1, .."
@ordinal(T)        an ORDER BY ordinal of the select list
@group_keys / (rollup) / (cube) / (sets)   GROUP BY keys; the level becomes grouped
@global_agg        the level becomes a global aggregate (no GROUP BY)
@derived_alias     alias of a derived table whose columns are c0.. of the current shape
@cte_name          name of a CTE with the current shape
@define_alias(T,..) / @define_alias(-, T, ..)  alias (+ column list) of a set-returning function / JSON_TABLE
@define_rel(name, T, ..)               make a relation visible (recursive CTE)
@join_eq           a hash/merge-joinable equality between the two inputs of the current join (@frame rules)
@sorted_agg(FUNC, T, extra..)          FUNC(e, extra ORDER BY e): order-sensitive aggregate made deterministic
@target / @target(plain) / @target(nopk)   DML / DDL target table (writable)
@target_col(T, pk|distinct|writable)   a column of the target
@insert_body / (values, one)           column list + VALUES rows or a query, respecting NOT NULL / keys
@assign            SET col = value, ...
@new_table / (partitioned|view|matview|shape)  a fresh table name (n1, n2, ..); @new_col(T, flags) / @newrel_col(T) / @fill
@fresh_name(p)     a fresh name; @target_name the target's name; @shape_list(rule) one rule<T> per shape type; @out"""

CONVENTIONS = """\
* Every binary operator is parenthesised: "(" expr<int> "+" expr<int> ")".
* Column references come only from @col / @target_col (never write a column name as literal text).
* Results must not depend on row order or the plan: no LIMIT without ORDER BY, no volatile functions
  (random(), clock_timestamp(), nextval()), order-sensitive aggregates through @sorted_agg.
* Prefer new alternatives of existing rules (expr<bool>, expr<T>, from_item, select_core, setup_stmt,
  create_table, stmt, ...) with small weights (<0.5> .. <2>) over new top-level rules.
* A new rule name must not clash with existing names; attributes (@scope, @frame, ...) apply to every variant
  of a rule name, so add attributes only to new rule names.
* Do not add %type or %start lines. Types available: the %type names in the grammar below.
* Use only the builtins listed above, with the argument forms shown.
* Keep it small: 1-8 alternatives that reach the changed code; quality over coverage of the whole feature."""


def system_prompt(grammar_path: str | Path, schema_path: str | Path) -> str:
    grammar = Path(grammar_path).read_text(encoding="utf-8")
    schema = Path(schema_path).read_text(encoding="utf-8")
    return "\n\n".join([
        "You extend a typed grammar that a fuzzer uses to generate SQL for PostgreSQL (assert-enabled master). "
        "The fuzzer runs every generated test case, looks for crashes, assertion failures, internal errors, and "
        "wrong results (plan-variant and metamorphic oracles), and keeps test cases that reach new features. "
        "Given one recent PostgreSQL commit, you propose grammar alternatives that make the generator reach the "
        "code that commit changed, so that thousands of variations of that SQL are tested.",
        "## The .pgg grammar format\n" + (dsl.__doc__ or "").strip(),
        "## Builtins (implemented in Python; anything else must be grammar text)\n" + BUILTINS,
        "## Conventions the fragment must follow\n" + CONVENTIONS,
        "## Database schema (schema.yaml; the same tables exist on the server)\n```yaml\n" + schema.strip() + "\n```",
        "## The current grammar\n```\n" + grammar.strip() + "\n```",
        "Seeds are plain SQL against the schema above. They may create their own tables (they run inside a "
        "transaction that is rolled back). Answer only with the JSON object described by the output schema.",
    ])


def commit_message(c: CommitDigest) -> str:
    targets = "\n".join(f"  {f}: {len(ls)} changed lines" for f, ls in sorted(c.targets.items()))
    return "\n".join([
        f"Commit {c.sha[:12]} ({c.date}): {c.subject}",
        "",
        c.body.strip(),
        "",
        "Files changed:\n" + "\n".join(f"  {f}" for f in c.files),
        "Functions changed: " + (", ".join(c.functions) or "(none recognised)"),
        "Diff-coverage targets (your alternatives should execute these lines):\n" + targets,
        "",
        "SQL this commit added to the regression tests:",
        "```sql",
        c.regress_sql.strip(),
        "```",
        "",
        "Propose the grammar fragment and seeds.",
    ])


def feedback_message(report: dict) -> str:
    """The validation gate's findings, sent back for a repair round."""
    lines = ["Your proposal did not pass the validation gate. Findings:"]
    for k in ("parse", "reachability", "validity", "seeds", "coverage"):
        if k in report:
            lines.append(f"- {k}: {json.dumps(report[k])[:1500]}")
    lines.append("Fix the fragment (and seeds) and answer again with the complete JSON object.")
    return "\n".join(lines)
