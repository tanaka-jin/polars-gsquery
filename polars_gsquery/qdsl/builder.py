from __future__ import annotations

from dataclasses import dataclass

from polars_gsquery.config import ConfigRef

from .ast import Agg, Column, Order, Predicate, QueryExpr, RawPredicate


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
    def from_sheet(
        self,
        data_sheet: str,
        config_sheet: str | None = None,
        header_rows: int = 1,
        range_: str | None = None,
    ) -> QueryExpr:
        return QueryExpr(data_sheet=data_sheet, config_sheet=config_sheet, range_=range_, header_rows=header_rows)

    def col(self, name: str) -> ColExpr:
        return ColExpr(Column(name))

    def sum(self, name: str) -> Agg:
        return Agg("sum", name)

    def count(self, name: str) -> Agg:
        return Agg("count", name)

    def cfg(self, key: str, type_name: str = "string") -> ConfigRef:
        return ConfigRef(key=key, type_name=type_name, a1_ref=f"__CONFIG_KEY__:{key}")

    def raw(self, query: str, /, **columns: ColExpr) -> RawPredicate:
        named_columns: list[tuple[str, Column]] = []
        for alias, col_expr in columns.items():
            if not isinstance(col_expr, ColExpr):
                raise TypeError(f"raw() placeholder must be q.col(...): {alias}={col_expr!r}")
            named_columns.append((alias, col_expr.col))
        return RawPredicate(query=query, named_columns=tuple(named_columns))

    def desc(self, name: str) -> Order:
        return Order(name=name, descending=True)

    def asc(self, name: str) -> Order:
        return Order(name=name, descending=False)


q = QueryNamespace()
