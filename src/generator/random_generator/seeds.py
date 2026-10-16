"""
Seed corpus for the random/mutation generator.

Seeds are authored as structured AST objects (not hand-written strings)
so they're guaranteed syntactically valid and stay consistent with the
shared query representation used across all three generator stages.
They are serialized to SQL text once; from there the mutation engine
treats them as plain strings.
"""

from __future__ import annotations
from typing import List

from generator.common.ast_nodes import (
    SelectQuery, SelectItem, ColumnRef, Star, TableRef, BinaryExpr, Literal,
    JoinClause, OrderByItem, InsertQuery, SetClause, UpdateQuery, DeleteQuery,
)
from generator.common.schema import Schema, default_demo_schema


# Literals the baseline knows how to spell. Other types are selected with *
# but not inserted, so a seed does not fail on a range or an array literal.
_LITERAL_TYPES = {
    "int": ("int", 1),
    "integer": ("int", 1),
    "bigint": ("int", 1),
    "text": ("string", "a"),
    "float8": ("float", 1.5),
    "float": ("float", 1.5),
    "numeric": ("float", 1.5),
    "bool": ("bool", True),
    "boolean": ("bool", True),
}


def _literal(column):
    kind, value = _LITERAL_TYPES[column.type_]
    return Literal(value, kind)


def _corpus_seeds(schema: Schema) -> List[str]:
    """Valid seeds against corpus/schema.sql. Mutation is then free to break them."""
    from generator.common.ast_nodes import FunctionCall

    bases = schema.base_tables()
    if not bases:
        raise ValueError("schema has no base tables to seed from")
    seeds: List[str] = []
    for table in bases:
        seeds.append(SelectQuery(
            select_items=[SelectItem(Star())],
            from_table=TableRef(table.name),
            limit=5,
        ).to_sql())
        writable = [c for c in table.columns if c.writable and c.type_ in _LITERAL_TYPES]
        if not writable:
            continue
        col = writable[0]
        seeds.append(SelectQuery(
            select_items=[SelectItem(ColumnRef(col.name))],
            from_table=TableRef(table.name),
            where=BinaryExpr(ColumnRef(col.name), "=", _literal(col)),
            limit=10,
        ).to_sql())

    t0, t1 = schema.get_table("t0"), schema.get_table("t1")
    if t0 and t1:
        seeds.append(SelectQuery(
            select_items=[SelectItem(ColumnRef("c1", "a"))],
            from_table=TableRef(t0.name, "a"),
            joins=[JoinClause(
                table=TableRef(t1.name, "b"),
                join_type="JOIN",
                on_expr=BinaryExpr(ColumnRef("c0", "a"), "=", ColumnRef("c0", "b")),
            )],
        ).to_sql())
        seeds.append(SelectQuery(
            select_items=[SelectItem(ColumnRef("c0")), SelectItem(FunctionCall("count", [Star()]), alias="n")],
            from_table=TableRef(t0.name),
            group_by=[ColumnRef("c0")],
        ).to_sql())

    for table in bases:
        cols = [c for c in table.columns if c.writable and c.type_ in _LITERAL_TYPES]
        if not cols:
            continue
        seeds.append(InsertQuery(
            table=table.name,
            columns=[c.name for c in cols],
            rows=[[_literal(c) for c in cols]],
        ).to_sql())
        seeds.append(UpdateQuery(
            table=table.name,
            set_clauses=[SetClause(cols[0].name, _literal(cols[0]))],
            where=BinaryExpr(ColumnRef(cols[0].name), "=", _literal(cols[0])),
        ).to_sql())
        seeds.append(DeleteQuery(
            table=table.name,
            where=BinaryExpr(ColumnRef(cols[0].name), "=", _literal(cols[0])),
        ).to_sql())
        break
    return seeds


def build_seed_queries(schema: Schema) -> List[str]:
    """Return a list of seed SQL strings derived from `schema`."""
    if schema.get_table("users") is None:
        return _corpus_seeds(schema)
    users = schema.get_table("users")
    orders = schema.get_table("orders")
    products = schema.get_table("products")

    seeds = []

    # Plain SELECT *
    seeds.append(SelectQuery(
        select_items=[SelectItem(Star())],
        from_table=TableRef(users.name),
    ).to_sql())

    # SELECT with WHERE and LIMIT
    seeds.append(SelectQuery(
        select_items=[SelectItem(ColumnRef("id")), SelectItem(ColumnRef("name"))],
        from_table=TableRef(users.name),
        where=BinaryExpr(ColumnRef("age"), ">", Literal(18, "int")),
        order_by=[OrderByItem(ColumnRef("id"), "DESC")],
        limit=10,
    ).to_sql())

    # JOIN across two tables
    seeds.append(SelectQuery(
        select_items=[SelectItem(ColumnRef("name", "u")), SelectItem(ColumnRef("total", "o"))],
        from_table=TableRef(users.name, "u"),
        joins=[JoinClause(
            table=TableRef(orders.name, "o"),
            join_type="JOIN",
            on_expr=BinaryExpr(ColumnRef("id", "u"), "=", ColumnRef("user_id", "o")),
        )],
        where=BinaryExpr(ColumnRef("status", "o"), "=", Literal("paid", "string")),
    ).to_sql())

    # Aggregate / GROUP BY
    from generator.common.ast_nodes import FunctionCall
    seeds.append(SelectQuery(
        select_items=[SelectItem(ColumnRef("status")), SelectItem(FunctionCall("COUNT", [Star()]), alias="cnt")],
        from_table=TableRef(orders.name),
        group_by=[ColumnRef("status")],
    ).to_sql())

    # INSERT
    seeds.append(InsertQuery(
        table=products.name,
        columns=["title", "price", "in_stock"],
        rows=[[Literal("Widget", "string"), Literal(9.99, "float"), Literal(True, "bool")]],
    ).to_sql())

    # UPDATE
    seeds.append(UpdateQuery(
        table=users.name,
        set_clauses=[SetClause("is_active", Literal(False, "bool"))],
        where=BinaryExpr(ColumnRef("id"), "=", Literal(1, "int")),
    ).to_sql())

    # DELETE
    seeds.append(DeleteQuery(
        table=orders.name,
        where=BinaryExpr(ColumnRef("status"), "=", Literal("cancelled", "string")),
    ).to_sql())

    return seeds


def default_seed_corpus() -> List[str]:
    return build_seed_queries(default_demo_schema())
