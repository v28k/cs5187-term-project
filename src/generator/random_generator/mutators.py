"""
Mutation operators for the random/mutation baseline.

These operate on raw SQL *text*, not the AST -- deliberately, since this
is the "no grammar knowledge" configuration we compare against. Each
mutator takes a string and an rng, and returns a (possibly invalid)
mutated string. Operators are inspired by classic byte/token-level
mutators (AFL-style) adapted to a textual, token-aware fuzzer so the
baseline isn't *purely* byte-garbage (which would almost always be
rejected at the lexer) but still has no grammar/semantic awareness.
"""

from __future__ import annotations
import random
import string
from typing import Callable, List

KEYWORDS = [
    "SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "GROUP BY", "ORDER BY",
    "LIMIT", "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE FROM",
    "UNION", "UNION ALL", "DISTINCT", "HAVING", "AS", "NULL", "NOT",
]

OPERATORS = ["=", "!=", "<>", "<", ">", "<=", ">=", "AND", "OR", "LIKE", "IN"]

BOUNDARY_INTS = ["-1", "0", "1", "2147483647", "-2147483648", "9223372036854775807",
                 "99999999999999999999"]

SPECIAL_STRINGS = ["", "' OR '1'='1", "\\", "%", "NULL", "''", "\"", ";--", "/*", "*/"]


def _rand_token_index(sql: str, rng: random.Random) -> int:
    """Pick a random character offset into the string (helper for several mutators)."""
    return rng.randrange(0, max(len(sql), 1))


def mutate_flip_char(sql: str, rng: random.Random) -> str:
    """Flip a single character to a random printable ASCII character."""
    if not sql:
        return sql
    i = _rand_token_index(sql, rng)
    chars = list(sql)
    chars[i] = rng.choice(string.printable[:94])  # printable, non-whitespace-heavy set
    return "".join(chars)


def mutate_delete_chunk(sql: str, rng: random.Random) -> str:
    """Delete a random contiguous chunk of characters."""
    if len(sql) < 2:
        return sql
    start = rng.randrange(0, len(sql) - 1)
    length = rng.randint(1, min(10, len(sql) - start))
    return sql[:start] + sql[start + length:]


def mutate_duplicate_chunk(sql: str, rng: random.Random) -> str:
    """Duplicate a random contiguous chunk, inserted right after itself."""
    if len(sql) < 2:
        return sql
    start = rng.randrange(0, len(sql) - 1)
    length = rng.randint(1, min(15, len(sql) - start))
    chunk = sql[start:start + length]
    insert_at = start + length
    return sql[:insert_at] + chunk + sql[insert_at:]


def mutate_insert_keyword(sql: str, rng: random.Random) -> str:
    """Splice a random SQL keyword in at a random position."""
    i = _rand_token_index(sql, rng)
    kw = rng.choice(KEYWORDS)
    return sql[:i] + f" {kw} " + sql[i:]


def mutate_swap_operator(sql: str, rng: random.Random) -> str:
    """Replace the first occurrence of a comparison/logical operator with another."""
    present = [op for op in OPERATORS if op in sql]
    if not present:
        return sql
    old = rng.choice(present)
    new = rng.choice([op for op in OPERATORS if op != old])
    return sql.replace(old, new, 1)


def mutate_boundary_int(sql: str, rng: random.Random) -> str:
    """Replace the first integer literal found with a boundary-value integer."""
    import re
    match = re.search(r"-?\b\d+\b", sql)
    if not match:
        return sql
    repl = rng.choice(BOUNDARY_INTS)
    return sql[:match.start()] + repl + sql[match.end():]


def mutate_special_string(sql: str, rng: random.Random) -> str:
    """Replace the first quoted string literal with a special/edge-case string."""
    import re
    match = re.search(r"'([^']*)'", sql)
    if not match:
        return sql
    repl = rng.choice(SPECIAL_STRINGS)
    escaped = repl.replace("'", "''")
    return sql[:match.start()] + f"'{escaped}'" + sql[match.end():]


def mutate_drop_clause(sql: str, rng: random.Random) -> str:
    """Drop a trailing clause (WHERE/ORDER BY/LIMIT/GROUP BY) if present."""
    import re
    for clause in ["LIMIT", "ORDER BY", "GROUP BY", "WHERE", "HAVING"]:
        pattern = re.compile(rf"\s+{clause}\b.*?(?=;|$)", re.IGNORECASE)
        if pattern.search(sql):
            if rng.random() < 0.5:
                return pattern.sub("", sql, count=1)
    return sql


def mutate_repeat_statement(sql: str, rng: random.Random) -> str:
    """Stack the statement on itself (tests multi-statement / batched execution)."""
    return sql.rstrip() + " " + sql.strip()


# Registry of all available mutators, used by the generator to pick randomly.
ALL_MUTATORS: List[Callable[[str, random.Random], str]] = [
    mutate_flip_char,
    mutate_delete_chunk,
    mutate_duplicate_chunk,
    mutate_insert_keyword,
    mutate_swap_operator,
    mutate_boundary_int,
    mutate_special_string,
    mutate_drop_clause,
    mutate_repeat_statement,
]
