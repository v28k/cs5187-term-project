from __future__ import annotations

from pathlib import Path
from typing import Any

from pgfuzz.core.interfaces import Generator, GeneratorContext
from pgfuzz.core.sqlsplit import split_statements
from pgfuzz.core.types import TestCase
from pgfuzz.eval.features import tokenize


def _sql_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(p.rglob("*.sql"))
        elif p.exists():
            files.append(p)
        else:
            raise FileNotFoundError(f"corpus path not found: {p}")
    if not files:
        raise FileNotFoundError(f"no .sql files in {paths}")
    return files


class CorpusGenerator(Generator):
    """Replays ``.sql`` files. ``unit: file`` makes one test case per file (PoCs);
    ``unit: statement`` makes one test case per statement (seed corpora)."""

    name = "corpus"

    def __init__(self, paths: list[str] | str, unit: str = "file", loop: bool = False, shuffle: bool = False) -> None:
        self.paths = [paths] if isinstance(paths, str) else list(paths)
        if unit not in ("file", "statement"):
            raise ValueError("unit must be 'file' or 'statement'")
        self.unit, self.loop, self.shuffle = unit, loop, shuffle
        self.items: list[tuple[str, list[str]]] = []
        self.pos = 0

    def setup(self, ctx: GeneratorContext) -> None:
        super().setup(ctx)
        for f in _sql_files(self.paths):
            stmts = split_statements(f.read_text(encoding="utf-8"))
            if self.unit == "file":
                self.items.append((f.name, stmts))
            else:
                self.items += [(f"{f.name}#{i + 1}", [s]) for i, s in enumerate(stmts)]
        if self.shuffle:
            ctx.rng.shuffle(self.items)

    def next_testcase(self) -> TestCase | None:
        if self.pos >= len(self.items):
            if not self.loop or not self.items:
                return None
            self.pos = 0
        src, stmts = self.items[self.pos]
        self.pos += 1
        return TestCase(list(stmts), origin=self.name, meta={"source": src})

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "paths": self.paths, "unit": self.unit, "items": len(self.items)}


_KEYWORDS = (
    "SELECT FROM WHERE GROUP BY HAVING ORDER LIMIT OFFSET JOIN LEFT RIGHT FULL INNER CROSS ON USING AS AND OR "
    "NOT NULL IS IN EXISTS BETWEEN LIKE CASE WHEN THEN ELSE END UNION ALL INTERSECT EXCEPT DISTINCT WITH "
    "RECURSIVE LATERAL OVER PARTITION WINDOW ROWS RANGE INSERT INTO VALUES UPDATE SET DELETE CREATE TABLE "
    "INDEX VIEW DROP ALTER ADD COLUMN PRIMARY KEY REFERENCES CHECK DEFAULT RETURNING CAST TRUE FALSE ANY "
    "ARRAY ROW FILTER COLLATE"
).split()
_OPS = "= <> < > <= >= + - * / % || :: ( ) , . [ ]".split()
_FUNCS = "count sum avg min max abs coalesce nullif length lower upper substr row_number rank lag lead array_agg string_agg".split()
_TYPES = "int bigint text numeric float8 bool date timestamp jsonb int4range".split()


class RandomGenerator(Generator):
    """Minimal unguided baseline.

    ``mode: random``   statements are random sequences of SQL keywords, schema
                       identifiers, functions, literals and operators.
    ``mode: mutation`` statements are seed statements with random token-level
                       mutations (delete, duplicate, replace, insert, swap, splice).
    ``mode: mixed``    50/50.

    A stand-in so the pipeline runs before Member B's random/mutation baseline exists.
    """

    name = "random"

    def __init__(
        self,
        mode: str = "mixed",
        seeds: list[str] | str | None = None,
        tables: dict[str, list[str]] | None = None,
        min_len: int = 3,
        max_len: int = 30,
        max_statements: int = 3,
        max_mutations: int = 4,
    ) -> None:
        if mode not in ("random", "mutation", "mixed"):
            raise ValueError("mode must be random, mutation or mixed")
        self.mode = mode
        self.seed_paths = [seeds] if isinstance(seeds, str) else list(seeds or [])
        if mode != "random" and not self.seed_paths:
            raise ValueError(f"mode {mode!r} needs 'seeds'")
        self.tables = tables or {"t0": ["c0", "c1", "c2"], "t1": ["c0", "c1"]}
        self.min_len, self.max_len = min_len, max_len
        self.max_statements, self.max_mutations = max_statements, max_mutations
        self.seed_tokens: list[list[str]] = []

    def setup(self, ctx: GeneratorContext) -> None:
        super().setup(ctx)
        self.rng = ctx.rng
        if self.seed_paths:
            for f in _sql_files(self.seed_paths):
                for s in split_statements(f.read_text(encoding="utf-8")):
                    toks = [t for _, t in tokenize(s)]
                    if toks:
                        self.seed_tokens.append(toks)
        self.vocab = (_KEYWORDS + _OPS + _FUNCS + _TYPES + list(self.tables)
                      + [c for cols in self.tables.values() for c in cols])

    def _literal(self) -> str:
        r = self.rng.random()
        if r < 0.4:
            return str(self.rng.choice([0, 1, -1, 2, 10, 2**31 - 1, -(2**31), 2**63 - 1, self.rng.randint(-1000, 1000)]))
        if r < 0.6:
            return self.rng.choice(["0.5", "1e308", "-0.0", "'NaN'::float8", "'infinity'::float8"])
        if r < 0.85:
            return "'" + self.rng.choice(["", "a", "abc", "%", "_", "{1,2}", '{"a": 1}', "[1,10)", "2024-02-29"]) + "'"
        return "NULL"

    def _token(self) -> str:
        return self._literal() if self.rng.random() < 0.15 else self.rng.choice(self.vocab)

    def _random_stmt(self) -> str:
        n = self.rng.randint(self.min_len, self.max_len)
        head = self.rng.choice(["SELECT", "SELECT", "SELECT", "INSERT INTO", "UPDATE", "DELETE FROM", "WITH", "CREATE TABLE"])
        return " ".join([head] + [self._token() for _ in range(n)])

    def _mutate(self) -> str:
        toks = list(self.rng.choice(self.seed_tokens))
        for _ in range(self.rng.randint(1, self.max_mutations)):
            op = self.rng.randrange(6)
            i = self.rng.randrange(len(toks)) if toks else 0
            if op == 0 and len(toks) > 1:
                del toks[i]
            elif op == 1 and toks:
                toks.insert(i, toks[i])
            elif op == 2 and toks:
                toks[i] = self._token()
            elif op == 3:
                toks.insert(i, self._token())
            elif op == 4 and len(toks) > 1:
                j = self.rng.randrange(len(toks))
                toks[i], toks[j] = toks[j], toks[i]
            else:
                other = self.rng.choice(self.seed_tokens)
                a = self.rng.randrange(len(other))
                b = self.rng.randrange(a, len(other)) + 1
                toks[i:i] = other[a:b]
        return " ".join(toks)

    def next_testcase(self) -> TestCase | None:
        stmts, ops = [], []
        for _ in range(self.rng.randint(1, self.max_statements)):
            use_mut = self.mode == "mutation" or (self.mode == "mixed" and self.rng.random() < 0.5)
            stmts.append(self._mutate() if use_mut else self._random_stmt())
            ops.append("mutation" if use_mut else "random")
        return TestCase(stmts, origin=self.name, meta={"ops": ops})

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "mode": self.mode, "seed_statements": len(self.seed_tokens),
                "seeds": self.seed_paths}
