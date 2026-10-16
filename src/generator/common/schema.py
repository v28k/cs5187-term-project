"""
Minimal schema model.

The random/mutation generator is intentionally schema-light (it does not
need to understand PostgreSQL's grammar), but it still needs *some* idea
of what tables/columns exist so that seed queries reference real objects
in the target database. Grammar-only and grammar+LLM generators (later
stages) will use a richer version of this same Schema object.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import random


@dataclass
class Column:
    name: str
    type_: str          # e.g. "integer", "text", "boolean", "numeric", "timestamp"
    nullable: bool = True
    is_primary_key: bool = False
    writable: bool = True


@dataclass
class Table:
    name: str
    columns: List[Column] = field(default_factory=list)
    kind: str = "table"

    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    def random_column(self, rng: random.Random) -> Column:
        return rng.choice(self.columns)

    def columns_of_type(self, type_: str) -> List[Column]:
        return [c for c in self.columns if c.type_ == type_]


@dataclass
class Schema:
    tables: List[Table] = field(default_factory=list)

    def table_names(self) -> List[str]:
        return [t.name for t in self.tables]

    def get_table(self, name: str) -> Optional[Table]:
        for t in self.tables:
            if t.name == name:
                return t
        return None

    def random_table(self, rng: random.Random) -> Table:
        return rng.choice(self.tables)

    def base_tables(self) -> List[Table]:
        """Tables a statement may read or write. Views are readable only."""
        return [t for t in self.tables if t.kind in ("table", "partitioned")]


def default_demo_schema() -> Schema:
    """A small, self-contained schema used for local testing and demos.

    In the real evaluation harness this will be replaced with a Schema
    introspected from an actual PostgreSQL test database (via
    information_schema), but having a static demo schema lets the
    generator and its tests run without a live PostgreSQL instance.
    """
    users = Table(
        name="users",
        columns=[
            Column("id", "integer", nullable=False, is_primary_key=True),
            Column("name", "text"),
            Column("email", "text"),
            Column("age", "integer"),
            Column("is_active", "boolean"),
            Column("created_at", "timestamp"),
        ],
    )
    orders = Table(
        name="orders",
        columns=[
            Column("id", "integer", nullable=False, is_primary_key=True),
            Column("user_id", "integer"),
            Column("total", "numeric"),
            Column("status", "text"),
            Column("created_at", "timestamp"),
        ],
    )
    products = Table(
        name="products",
        columns=[
            Column("id", "integer", nullable=False, is_primary_key=True),
            Column("title", "text"),
            Column("price", "numeric"),
            Column("in_stock", "boolean"),
        ],
    )
    return Schema(tables=[users, orders, products])


def schema_from_corpus(path: str) -> Schema:
    """The shared ``corpus/schema.yaml``, in this package's Schema type.

    The grammar arm reads the same file through ``pgfuzz.grammar.schema``.
    Keeping one description means both arms target the same tables.
    """
    from pgfuzz.grammar.schema import load_schema

    loaded = load_schema(path)
    tables = [
        Table(
            name=rel.name,
            kind=rel.kind,
            columns=[
                Column(
                    c.name,
                    c.type,
                    nullable="notnull" not in c.flags and "pk" not in c.flags,
                    is_primary_key="pk" in c.flags,
                    writable=c.writable,
                )
                for c in rel.columns
            ],
        )
        for rel in loaded.relations.values()
    ]
    return Schema(tables=tables)
