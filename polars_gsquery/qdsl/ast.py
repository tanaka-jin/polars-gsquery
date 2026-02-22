from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


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


@dataclass(frozen=True)
class QueryExpr:
    data_sheet: str
    config_sheet: str | None
    range_: str
    header_rows: int
    selected: tuple[object, ...] = ()
    predicates: tuple[Predicate, ...] = ()
    group_keys: tuple[str, ...] = ()
    order: tuple[Order, ...] = ()
    limit_n: int | None = None

    def select(self, items: Sequence[object]) -> "QueryExpr":
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=(*self.selected, *items),
            predicates=self.predicates,
            group_keys=self.group_keys,
            order=self.order,
            limit_n=self.limit_n,
        )

    def where(self, predicate: Predicate) -> "QueryExpr":
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=self.selected,
            predicates=(*self.predicates, predicate),
            group_keys=self.group_keys,
            order=self.order,
            limit_n=self.limit_n,
        )

    def groupby(self, keys: Sequence[str]) -> "QueryExpr":
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=self.selected,
            predicates=self.predicates,
            group_keys=tuple(keys),
            order=self.order,
            limit_n=self.limit_n,
        )

    def orderby(self, items: Sequence[Order]) -> "QueryExpr":
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=self.selected,
            predicates=self.predicates,
            group_keys=self.group_keys,
            order=tuple(items),
            limit_n=self.limit_n,
        )

    def limit(self, n: int) -> "QueryExpr":
        if n < 0:
            raise ValueError("limit must be >= 0")
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=self.selected,
            predicates=self.predicates,
            group_keys=self.group_keys,
            order=self.order,
            limit_n=n,
        )
