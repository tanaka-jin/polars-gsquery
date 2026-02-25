from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from polars_gsquery.config import ConfigRef
from polars_gsquery.sheets.a1 import quote_sheet_name
from polars_gsquery.sheets.locale import function_arg_delimiter, quote_formula_string

from .ast import Agg, Column, Order, Predicate, QueryExpr, RawExpr

COLN_API_ERROR = (
    "ColN style column references are not supported in the Python API. "
    "Use column names or aliases. If you need raw QUERY syntax, use q.raw()."
)


def _is_coln_reference(name: str) -> bool:
    return bool(re.fullmatch(r"col\d+", name, flags=re.IGNORECASE))


@dataclass
class CompiledQuery:
    formula: str
    query_text: str


def compile_formula(expr: QueryExpr, header_map: dict[str, str], locale: str) -> CompiledQuery:
    query_text, dynamic = _render_query_text(expr, header_map)
    delim = function_arg_delimiter(locale)
    query_expr = _inject_dynamic_tokens(query_text, dynamic, delim)
    data_range = _resolve_range(expr, header_map)
    formula = f"=QUERY({quote_sheet_name(expr.data_sheet)}!{data_range}{delim} {query_expr}{delim} {expr.header_rows})"
    return CompiledQuery(
        formula=formula,
        query_text=query_text,
    )


def _render_query_text(expr: QueryExpr, header_map: dict[str, str]) -> tuple[str, list[tuple[str, ConfigRef]]]:
    query_parts: list[str] = []
    dynamic: list[tuple[str, ConfigRef]] = []
    labels: list[tuple[str, str]] = []
    aliases: dict[str, str] = {}

    query_parts.append(f"select {_compile_select(expr.selected, header_map, labels, aliases)}")

    if expr.predicates:
        where_sql = " and ".join(_compile_predicate(p, header_map, dynamic) for p in expr.predicates)
        query_parts.append(f"where {where_sql}")
    if expr.group_keys:
        query_parts.append(f"group by {', '.join(_resolve_col(k, header_map) for k in expr.group_keys)}")
    if expr.order:
        query_parts.append(f"order by {_compile_order(expr.order, header_map, aliases)}")
    if expr.limit_n is not None:
        query_parts.append(f"limit {expr.limit_n}")
    if labels:
        label_sql = ", ".join(f"{target} '{_quote_query_string(label)}'" for target, label in labels)
        query_parts.append(f"label {label_sql}")

    return "\n".join(query_parts), dynamic


def _compile_select(
    items: Sequence[object],
    header_map: dict[str, str],
    labels: list[tuple[str, str]],
    aliases: dict[str, str],
) -> str:
    if not items:
        return "*"
    compiled: list[str] = []
    for item in items:
        if isinstance(item, str):
            compiled.append(_resolve_col(item, header_map))
        elif isinstance(item, RawExpr):
            compiled.append(_render_raw_expr(item, header_map))
        elif isinstance(item, Agg):
            col = _resolve_agg_column(item.column, header_map)
            target = f"{item.func}({col})"
            piece = target
            if item.alias_name:
                labels.append((target, item.alias_name))
                aliases[item.alias_name] = target
            compiled.append(piece)
        else:
            raise TypeError(f"Unsupported select item: {item!r}")
    return ", ".join(compiled)


def _resolve_agg_column(column: str | Column, header_map: dict[str, str]) -> str:
    if isinstance(column, Column):
        return _resolve_col(column.name, header_map)
    return _resolve_col(column, header_map)


def _compile_predicate(
    pred: Predicate | RawExpr, header_map: dict[str, str], dynamic: list[tuple[str, ConfigRef]]
) -> str:
    if isinstance(pred, RawExpr):
        return _render_raw_expr(pred, header_map)

    left = _resolve_col(pred.left.name, header_map)
    right = pred.right
    if isinstance(right, ConfigRef):
        token = f"__CFG_{len(dynamic)}__"
        dynamic.append((token, right))
        return f"{left} {pred.op} {token}"
    if isinstance(right, str):
        return f"{left} {pred.op} '{_quote_query_string(right)}'"
    if isinstance(right, bool):
        return f"{left} {pred.op} {'TRUE' if right else 'FALSE'}"
    return f"{left} {pred.op} {right}"


def _compile_order(orders: Sequence[Order], header_map: dict[str, str], aliases: dict[str, str]) -> str:
    out: list[str] = []
    for item in orders:
        col = _resolve_order_target(item.name, header_map, aliases)
        out.append(col + (" desc" if item.descending else " asc"))
    return ", ".join(out)


def _resolve_order_target(name: str, header_map: dict[str, str], aliases: dict[str, str]) -> str:
    if name in aliases:
        return aliases[name]
    if name in header_map:
        return header_map[name]
    if _is_coln_reference(name):
        raise KeyError(COLN_API_ERROR)
    raise KeyError(f"Unknown order key in header map: {name}")


def _inject_dynamic_tokens(query_text: str, dynamic: list[tuple[str, ConfigRef]], delim: str) -> str:
    if not dynamic:
        return quote_formula_string(query_text)
    pieces: list[str] = []
    cursor = 0
    for token, cfg_ref in dynamic:
        idx = query_text.index(token, cursor)
        static = query_text[cursor:idx]
        if static:
            pieces.append(quote_formula_string(static))
        pieces.append(_config_ref_expr(cfg_ref, delim))
        cursor = idx + len(token)
    if query_text[cursor:]:
        pieces.append(quote_formula_string(query_text[cursor:]))
    return " & ".join(pieces)


def _config_ref_expr(cfg_ref: ConfigRef, delim: str) -> str:
    if cfg_ref.type_name == "string":
        return f'"\'" & SUBSTITUTE({cfg_ref.a1_ref}{delim} "\'"{delim} "\'\'") & "\'"'
    if cfg_ref.type_name == "date":
        return f'"date \'" & TEXT({cfg_ref.a1_ref}{delim} "yyyy-MM-dd") & "\'"'
    if cfg_ref.type_name == "boolean":
        return f'IF({cfg_ref.a1_ref}{delim} "TRUE"{delim} "FALSE")'
    return cfg_ref.a1_ref


def _resolve_range(expr: QueryExpr, header_map: dict[str, str]) -> str:
    if expr.range_ is not None:
        return expr.range_
    if not header_map:
        raise ValueError("Cannot infer range from empty header")
    return f"A:{_a1_col_from_count(len(header_map))}"


def _a1_col_from_count(count: int) -> str:
    if count < 1:
        raise ValueError("count must be >= 1")

    out: list[str] = []
    n = count
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out.append(chr(ord("A") + rem))
    return "".join(reversed(out))


def _quote_query_string(value: str) -> str:
    return value.replace("'", "''")


def _resolve_col(name: str, header_map: dict[str, str]) -> str:
    if _is_coln_reference(name):
        raise KeyError(COLN_API_ERROR)
    if name not in header_map:
        raise KeyError(f"Unknown column in header map: {name}")
    return header_map[name]


def _render_raw_expr(raw: RawExpr, header_map: dict[str, str]) -> str:
    rendered = raw.query
    for alias, col in raw.named_columns:
        rendered = rendered.replace(f"{{{alias}}}", _resolve_col(col.name, header_map))
    return rendered
