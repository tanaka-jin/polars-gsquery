from __future__ import annotations

from .config import Config, ConfigRef
from .qdsl.ast import Predicate, QueryExpr, RawExpr

_DEFERRED_CONFIG_PREFIX = "__CONFIG_KEY__:"


def has_deferred_config_refs(expr: QueryExpr) -> bool:
    return any(
        isinstance(predicate, Predicate) and _is_deferred_config_ref(predicate.right) for predicate in expr.predicates
    )


def bind_config_refs(expr: QueryExpr, cfg: Config) -> QueryExpr:
    return QueryExpr(
        data_sheet=expr.data_sheet,
        config_sheet=expr.config_sheet,
        range_=expr.range_,
        header_rows=expr.header_rows,
        selected=expr.selected,
        predicates=tuple(_bind_predicate_config_ref(predicate, cfg) for predicate in expr.predicates),
        group_keys=expr.group_keys,
        order=expr.order,
        limit_n=expr.limit_n,
    )


def _bind_predicate_config_ref(predicate: Predicate | RawExpr, cfg: Config) -> Predicate | RawExpr:
    if isinstance(predicate, RawExpr):
        return predicate

    if not _is_deferred_config_ref(predicate.right):
        return predicate

    right = predicate.right
    assert isinstance(right, ConfigRef)
    key = right.a1_ref.removeprefix(_DEFERRED_CONFIG_PREFIX)
    return Predicate(left=predicate.left, op=predicate.op, right=cfg.ref(key))


def _is_deferred_config_ref(value: object) -> bool:
    return isinstance(value, ConfigRef) and value.a1_ref.startswith(_DEFERRED_CONFIG_PREFIX)
