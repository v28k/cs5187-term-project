"""
Query representation format (shared AST).

Design goals:
  - Small set of node types covering the common DML/DDL surface
    (SELECT / INSERT / UPDATE / DELETE / CREATE TABLE) that PostgreSQL
    bug-finding fuzzers typically target.
  - Every node knows how to render itself back to SQL text via to_sql(),
    so the same structured object can be (a) used directly by a future
    grammar-based generator, and (b) serialized to a string and handed
    to the random/mutation engine in this stage.
  - Nodes are plain dataclasses: easy to construct, copy, and mutate
    programmatically later (e.g. swapping an operator or a literal).

This module intentionally does NOT try to cover all of PostgreSQL's
grammar -- only what's needed to generate structurally valid baseline
queries. It is extended in later stages (grammar-only, grammar+LLM).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Union


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Node:
    """Base class for every AST node. Subclasses must implement to_sql()."""

    def to_sql(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} must implement to_sql()")

    def __str__(self) -> str:
        return self.to_sql()


# ---------------------------------------------------------------------------
# Leaf expressions
# ---------------------------------------------------------------------------

@dataclass
class Identifier(Node):
    name: str

    def to_sql(self) -> str:
        return self.name


@dataclass
class Literal(Node):
    """A scalar literal. `kind` in {"int", "float", "string", "bool", "null"}."""
    value: Union[int, float, str, bool, None]
    kind: str = "string"

    def to_sql(self) -> str:
        if self.kind == "null" or self.value is None:
            return "NULL"
        if self.kind == "bool":
            return "TRUE" if self.value else "FALSE"
        if self.kind in ("int", "float"):
            return str(self.value)
        # string: escape single quotes the PostgreSQL way
        escaped = str(self.value).replace("'", "''")
        return f"'{escaped}'"


@dataclass
class ColumnRef(Node):
    name: str
    table: Optional[str] = None

    def to_sql(self) -> str:
        return f"{self.table}.{self.name}" if self.table else self.name


@dataclass
class Star(Node):
    table: Optional[str] = None

    def to_sql(self) -> str:
        return f"{self.table}.*" if self.table else "*"


@dataclass
class BinaryExpr(Node):
    left: Node
    op: str
    right: Node

    def to_sql(self) -> str:
        return f"({self.left.to_sql()} {self.op} {self.right.to_sql()})"


@dataclass
class UnaryExpr(Node):
    op: str
    operand: Node

    def to_sql(self) -> str:
        return f"({self.op} {self.operand.to_sql()})"


@dataclass
class FunctionCall(Node):
    name: str
    args: List[Node] = field(default_factory=list)

    def to_sql(self) -> str:
        args_sql = ", ".join(a.to_sql() for a in self.args)
        return f"{self.name}({args_sql})"


# ---------------------------------------------------------------------------
# Query building blocks
# ---------------------------------------------------------------------------

@dataclass
class SelectItem(Node):
    expr: Node
    alias: Optional[str] = None

    def to_sql(self) -> str:
        base = self.expr.to_sql()
        return f"{base} AS {self.alias}" if self.alias else base


@dataclass
class TableRef(Node):
    name: str
    alias: Optional[str] = None

    def to_sql(self) -> str:
        return f"{self.name} AS {self.alias}" if self.alias else self.name


@dataclass
class JoinClause(Node):
    table: TableRef
    join_type: str = "JOIN"          # JOIN / LEFT JOIN / RIGHT JOIN / FULL JOIN
    on_expr: Optional[Node] = None

    def to_sql(self) -> str:
        on_sql = f" ON {self.on_expr.to_sql()}" if self.on_expr else ""
        return f"{self.join_type} {self.table.to_sql()}{on_sql}"


@dataclass
class OrderByItem(Node):
    expr: Node
    direction: str = "ASC"

    def to_sql(self) -> str:
        return f"{self.expr.to_sql()} {self.direction}"


# ---------------------------------------------------------------------------
# Top-level statements
# ---------------------------------------------------------------------------

@dataclass
class SelectQuery(Node):
    select_items: List[SelectItem]
    from_table: Optional[TableRef] = None
    joins: List[JoinClause] = field(default_factory=list)
    where: Optional[Node] = None
    group_by: List[Node] = field(default_factory=list)
    having: Optional[Node] = None
    order_by: List[OrderByItem] = field(default_factory=list)
    limit: Optional[int] = None
    distinct: bool = False

    def to_sql(self) -> str:
        parts = ["SELECT"]
        if self.distinct:
            parts.append("DISTINCT")
        parts.append(", ".join(i.to_sql() for i in self.select_items))
        if self.from_table:
            parts.append(f"FROM {self.from_table.to_sql()}")
        for j in self.joins:
            parts.append(j.to_sql())
        if self.where:
            parts.append(f"WHERE {self.where.to_sql()}")
        if self.group_by:
            parts.append("GROUP BY " + ", ".join(g.to_sql() for g in self.group_by))
        if self.having:
            parts.append(f"HAVING {self.having.to_sql()}")
        if self.order_by:
            parts.append("ORDER BY " + ", ".join(o.to_sql() for o in self.order_by))
        if self.limit is not None:
            parts.append(f"LIMIT {self.limit}")
        return " ".join(parts) + ";"


@dataclass
class InsertQuery(Node):
    table: str
    columns: List[str]
    rows: List[List[Node]]           # list of value-rows

    def to_sql(self) -> str:
        cols_sql = ", ".join(self.columns)
        rows_sql = ", ".join(
            "(" + ", ".join(v.to_sql() for v in row) + ")" for row in self.rows
        )
        return f"INSERT INTO {self.table} ({cols_sql}) VALUES {rows_sql};"


@dataclass
class SetClause(Node):
    column: str
    value: Node

    def to_sql(self) -> str:
        return f"{self.column} = {self.value.to_sql()}"


@dataclass
class UpdateQuery(Node):
    table: str
    set_clauses: List[SetClause]
    where: Optional[Node] = None

    def to_sql(self) -> str:
        set_sql = ", ".join(s.to_sql() for s in self.set_clauses)
        sql = f"UPDATE {self.table} SET {set_sql}"
        if self.where:
            sql += f" WHERE {self.where.to_sql()}"
        return sql + ";"


@dataclass
class DeleteQuery(Node):
    table: str
    where: Optional[Node] = None

    def to_sql(self) -> str:
        sql = f"DELETE FROM {self.table}"
        if self.where:
            sql += f" WHERE {self.where.to_sql()}"
        return sql + ";"


@dataclass
class ColumnDef(Node):
    name: str
    type_: str
    constraints: List[str] = field(default_factory=list)   # e.g. ["PRIMARY KEY", "NOT NULL"]

    def to_sql(self) -> str:
        parts = [self.name, self.type_] + self.constraints
        return " ".join(parts)


@dataclass
class CreateTableQuery(Node):
    table: str
    columns: List[ColumnDef]
    if_not_exists: bool = False

    def to_sql(self) -> str:
        ine = "IF NOT EXISTS " if self.if_not_exists else ""
        cols_sql = ", ".join(c.to_sql() for c in self.columns)
        return f"CREATE TABLE {ine}{self.table} ({cols_sql});"


# Convenience alias used by the generators: anything with a to_sql()
Query = Union[SelectQuery, InsertQuery, UpdateQuery, DeleteQuery, CreateTableQuery]
