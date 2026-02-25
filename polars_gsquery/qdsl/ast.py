from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Column:
    name: str


@dataclass(frozen=True)
class RawExpr:
    query: str
    named_columns: tuple[tuple[str, Column], ...] = ()


@dataclass(frozen=True)
class Agg:
    func: str
    column: str | Column
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

    def __and__(self, other: "Predicate | BooleanExpr") -> "BooleanExpr":
        return BooleanExpr(left=self, op="and", right=other)

    def __or__(self, other: "Predicate | BooleanExpr") -> "BooleanExpr":
        return BooleanExpr(left=self, op="or", right=other)


@dataclass(frozen=True)
class BooleanExpr:
    left: Predicate | "BooleanExpr"
    op: str
    right: Predicate | "BooleanExpr"

    def __and__(self, other: Predicate | "BooleanExpr") -> "BooleanExpr":
        return BooleanExpr(left=self, op="and", right=other)

    def __or__(self, other: Predicate | "BooleanExpr") -> "BooleanExpr":
        return BooleanExpr(left=self, op="or", right=other)


@dataclass(frozen=True)
class QueryExpr:
    data_sheet: str
    config_sheet: str | None
    range_: str | None
    header_rows: int
    selected: tuple[object, ...] = ()
    predicates: tuple[Predicate | BooleanExpr | RawExpr, ...] = ()
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

    def where(self, *predicates: Predicate | BooleanExpr | str | RawExpr) -> "QueryExpr":
        normalized: list[Predicate | BooleanExpr | RawExpr] = []
        for predicate in predicates:
            if isinstance(predicate, str):
                normalized.append(RawExpr(predicate))
            else:
                normalized.append(predicate)
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=self.selected,
            predicates=(*self.predicates, *normalized),
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
        if isinstance(items, str):
            raise TypeError("orderby() expects a sequence of q.asc()/q.desc() items, not a string")

        normalized = tuple(items)
        for item in normalized:
            if not isinstance(item, Order):
                raise TypeError(f"orderby() item must be Order (q.asc/q.desc), got: {item!r}")

        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=self.selected,
            predicates=self.predicates,
            group_keys=self.group_keys,
            order=normalized,
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

    def with_range(self, range_: str) -> "QueryExpr":
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=range_,
            header_rows=self.header_rows,
            selected=self.selected,
            predicates=self.predicates,
            group_keys=self.group_keys,
            order=self.order,
            limit_n=self.limit_n,
        )
