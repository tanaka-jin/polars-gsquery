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
    order: tuple[tuple[str, bool], ...] = ()
    limit_n: int | None = None

    def select(self, items: object | Sequence[object]) -> "QueryExpr":
        normalized = _normalize_items(items)
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=(*self.selected, *normalized),
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

    def group_by(self, keys: str | Sequence[str]) -> "QueryExpr":
        normalized = _normalize_items(keys)
        for key in normalized:
            if not isinstance(key, str):
                raise TypeError(f"group_by() key must be str, got: {key!r}")
        return QueryExpr(
            data_sheet=self.data_sheet,
            config_sheet=self.config_sheet,
            range_=self.range_,
            header_rows=self.header_rows,
            selected=self.selected,
            predicates=self.predicates,
            group_keys=tuple(normalized),
            order=self.order,
            limit_n=self.limit_n,
        )

    def sort(
        self,
        by: str | Sequence[str],
        descending: bool | Sequence[bool] = False,
    ) -> "QueryExpr":
        normalized = _normalize_sort_items(by, descending)
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


def _normalize_items(items: object | Sequence[object]) -> tuple[object, ...]:
    if isinstance(items, (str, Column, Agg, RawExpr)):
        return (items,)
    return tuple(items)


def _normalize_sort_items(
    by: str | Sequence[str],
    descending: bool | Sequence[bool],
) -> tuple[tuple[str, bool], ...]:
    if isinstance(by, str):
        by_items = (by,)
    else:
        by_items = tuple(by)

    if isinstance(descending, bool):
        descending_flags = (descending,) * len(by_items)
    else:
        descending_flags = tuple(descending)
        if len(descending_flags) != len(by_items):
            raise ValueError("sort() descending length must match by length")

    normalized: list[tuple[str, bool]] = []
    for item, is_desc in zip(by_items, descending_flags):
        if not isinstance(item, str):
            raise TypeError(f"sort() item must be str, got: {item!r}")
        if not isinstance(is_desc, bool):
            raise TypeError(f"sort() descending must be bool, got: {is_desc!r}")
        normalized.append((item, is_desc))
    return tuple(normalized)
