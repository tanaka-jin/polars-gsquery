from __future__ import annotations

from dataclasses import dataclass

from .ast import Agg, Column, Order, Predicate, QueryExpr


@dataclass(frozen=True)
class ColExpr:
    col: Column

    def _cmp(self, op: str, other: object) -> Predicate:
        return Predicate(left=self.col, op=op, right=other)

    def __eq__(self, other: object) -> Predicate:  # type: ignore[override]
        return self._cmp("=", other)

    def __ne__(self, other: object) -> Predicate:  # type: ignore[override]
        return self._cmp("!=", other)

    def __gt__(self, other: object) -> Predicate:
        return self._cmp(">", other)

    def __ge__(self, other: object) -> Predicate:
        return self._cmp(">=", other)

    def __lt__(self, other: object) -> Predicate:
        return self._cmp("<", other)

    def __le__(self, other: object) -> Predicate:
        return self._cmp("<=", other)


class QueryNamespace:
    def from_sheet(self, data_sheet: str, config_sheet: str, header_rows: int, range_: str) -> QueryExpr:
        return QueryExpr(data_sheet=data_sheet, config_sheet=config_sheet, range_=range_, header_rows=header_rows)

    def col(self, name: str) -> ColExpr:
        return ColExpr(Column(name))

    def sum(self, name: str) -> Agg:
        return Agg("sum", name)

    def count(self, name: str) -> Agg:
        return Agg("count", name)

    def desc(self, name: str) -> Order:
        return Order(name=name, descending=True)


q = QueryNamespace()
