"""The database schema the grammar generator targets (``corpus/schema.yaml``).

Column flags: ``pk`` (primary key / unique), ``notnull``, ``identity``
(GENERATED ALWAYS AS IDENTITY: not insertable or updatable), ``generated``
(generated column: not insertable or updatable).
Relation kinds: ``table``, ``partitioned``, ``view``, ``matview``, ``cte``, ``derived``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Column:
    name: str
    type: str
    flags: frozenset[str] = frozenset()

    @property
    def writable(self) -> bool:
        return not (self.flags & {"identity", "generated"})


@dataclass
class Relation:
    name: str
    columns: list[Column]
    kind: str = "table"
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def writable(self) -> bool:
        return self.kind in ("table", "partitioned")

    def col(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


@dataclass
class Schema:
    relations: dict[str, Relation]

    def copy(self) -> "Schema":
        return Schema(dict(self.relations))

    def add(self, rel: Relation) -> None:
        self.relations[rel.name] = rel


def _column(spec: Any) -> Column:
    if isinstance(spec, dict):
        return Column(str(spec["name"]), str(spec["type"]), frozenset(spec.get("flags", ())))
    name, typ, *flags = spec
    return Column(str(name), str(typ), frozenset(map(str, flags)))


def schema_from_dict(d: dict[str, Any]) -> Schema:
    rels: dict[str, Relation] = {}
    for name, spec in (d.get("relations") or d.get("tables") or {}).items():
        cols = [_column(c) for c in spec["columns"]]
        rels[name] = Relation(name, cols, spec.get("kind", "table"), dict(spec.get("meta", {})))
    return Schema(rels)


def load_schema(path: str | Path) -> Schema:
    import yaml

    return schema_from_dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def validate_schema(schema: Schema, types: set[str]) -> list[str]:
    return [f"{r.name}.{c.name}: unknown type {c.type!r}"
            for r in schema.relations.values() for c in r.columns if c.type not in types]
