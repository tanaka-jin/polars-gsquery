from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from polars_sheets_query.config import ConfigRef


@dataclass(frozen=True)
class Column:
    name: str


@dataclass(frozen=True)
class Agg:
    func: str
    column: str
    alias_name: str | None = None

    def alias(self, name: str) -> "Agg":
        return Agg(func=self.func, column=self.column, alias_name=name)


@dataclass(frozen=True)
class Order:
    name: str
    descending: bool = False


@dataclass(frozen=True)
class Predicate:
    left: Column
    op: str
    right: object


@dataclass
class QueryExpr:
    source_sheet: str
    range_: str
    header_rows: int
    selected: list[object] = field(default_factory=list)
    predicates: list[Predicate] = field(default_factory=list)
    group_keys: list[str] = field(default_factory=list)
    order: list[Order] = field(default_factory=list)
    limit_n: int | None = None

    def select(self, items: Sequence[object]) -> "QueryExpr":
        self.selected.extend(items)
        return self

    def where(self, predicate: Predicate) -> "QueryExpr":
        self.predicates.append(predicate)
        return self

    def groupby(self, keys: Sequence[str]) -> "QueryExpr":
        self.group_keys = list(keys)
        return self

    def orderby(self, items: Sequence[Order]) -> "QueryExpr":
        self.order = list(items)
        return self

    def limit(self, n: int) -> "QueryExpr":
        self.limit_n = n
        return self


Literal = str | int | float | bool | ConfigRef
