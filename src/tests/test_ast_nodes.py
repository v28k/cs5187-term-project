"""Unit tests for the shared query representation (generator.common.ast_nodes)."""

from generator.common.ast_nodes import (
    SelectQuery, SelectItem, ColumnRef, Star, TableRef, BinaryExpr, Literal,
    JoinClause, OrderByItem, InsertQuery, UpdateQuery, DeleteQuery, SetClause,
    CreateTableQuery, ColumnDef, FunctionCall,
)


def test_simple_select():
    q = SelectQuery(select_items=[SelectItem(Star())], from_table=TableRef("users"))
    assert q.to_sql() == "SELECT * FROM users;"


def test_select_with_where_and_limit():
    q = SelectQuery(
        select_items=[SelectItem(ColumnRef("id"))],
        from_table=TableRef("users"),
        where=BinaryExpr(ColumnRef("age"), ">", Literal(18, "int")),
        order_by=[OrderByItem(ColumnRef("id"), "DESC")],
        limit=5,
    )
    sql = q.to_sql()
    assert sql.startswith("SELECT id FROM users WHERE (age > 18)")
    assert "ORDER BY id DESC" in sql
    assert sql.endswith("LIMIT 5;")


def test_join():
    q = SelectQuery(
        select_items=[SelectItem(ColumnRef("name", "u"))],
        from_table=TableRef("users", "u"),
        joins=[JoinClause(
            table=TableRef("orders", "o"),
            join_type="LEFT JOIN",
            on_expr=BinaryExpr(ColumnRef("id", "u"), "=", ColumnRef("user_id", "o")),
        )],
    )
    assert "LEFT JOIN orders AS o ON (u.id = o.user_id)" in q.to_sql()


def test_string_literal_escaping():
    lit = Literal("O'Brien", "string")
    assert lit.to_sql() == "'O''Brien'"


def test_insert():
    q = InsertQuery(
        table="products",
        columns=["title", "price"],
        rows=[[Literal("Widget", "string"), Literal(9.99, "float")]],
    )
    assert q.to_sql() == "INSERT INTO products (title, price) VALUES ('Widget', 9.99);"


def test_update():
    q = UpdateQuery(
        table="users",
        set_clauses=[SetClause("is_active", Literal(False, "bool"))],
        where=BinaryExpr(ColumnRef("id"), "=", Literal(1, "int")),
    )
    assert q.to_sql() == "UPDATE users SET is_active = FALSE WHERE (id = 1);"


def test_delete():
    q = DeleteQuery(table="orders", where=BinaryExpr(ColumnRef("status"), "=", Literal("cancelled", "string")))
    assert q.to_sql() == "DELETE FROM orders WHERE (status = 'cancelled');"


def test_create_table():
    q = CreateTableQuery(
        table="t",
        columns=[ColumnDef("id", "integer", ["PRIMARY KEY"]), ColumnDef("name", "text")],
        if_not_exists=True,
    )
    assert q.to_sql() == "CREATE TABLE IF NOT EXISTS t (id integer PRIMARY KEY, name text);"


def test_function_call_and_group_by():
    q = SelectQuery(
        select_items=[SelectItem(ColumnRef("status")), SelectItem(FunctionCall("COUNT", [Star()]), alias="cnt")],
        from_table=TableRef("orders"),
        group_by=[ColumnRef("status")],
    )
    sql = q.to_sql()
    assert "COUNT(*) AS cnt" in sql
    assert "GROUP BY status" in sql


if __name__ == "__main__":
    import pytest, sys as _sys
    _sys.exit(pytest.main([__file__, "-v"]))
