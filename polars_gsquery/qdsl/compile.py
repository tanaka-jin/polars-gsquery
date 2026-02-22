from __future__ import annotations

from dataclasses import dataclass

from polars_gsquery.config import ConfigRef
from polars_gsquery.sheets.locale import function_arg_delimiter, quote_formula_string

from .ast import Agg, Order, Predicate, QueryExpr


@dataclass
class CompiledQuery:
    formula: str
    query_text: str


def compile_formula(expr: QueryExpr, header_map: dict[str, str], locale: str) -> CompiledQuery:
    query_parts: list[str] = []
    dynamic: list[tuple[str, ConfigRef]] = []

    query_parts.append(f"select {_compile_select(expr.selected, header_map)}")

    if expr.predicates:
        where_sql = " and ".join(_compile_predicate(p, header_map, dynamic) for p in expr.predicates)
        query_parts.append(f"where {where_sql}")
    if expr.group_keys:
        query_parts.append(f"group by {', '.join(_resolve_col(k, header_map) for k in expr.group_keys)}")
    if expr.order:
        query_parts.append(f"order by {_compile_order(expr.order, header_map)}")
    if expr.limit_n is not None:
        query_parts.append(f"limit {expr.limit_n}")

    query_text = " ".join(query_parts)
    query_expr = _inject_dynamic_tokens(query_text, dynamic)
    delim = function_arg_delimiter(locale)
    return CompiledQuery(
        formula=f"=QUERY({expr.data_sheet}!{expr.range_}{delim} {query_expr}{delim} {expr.header_rows})",
        query_text=query_text,
    )


def _compile_select(items: list[object], header_map: dict[str, str]) -> str:
    if not items:
        return "*"
    compiled: list[str] = []
    for item in items:
        if isinstance(item, str):
            compiled.append(_resolve_col(item, header_map))
        elif isinstance(item, Agg):
            col = _resolve_col(item.column, header_map)
            piece = f"{item.func}({col})"
            if item.alias_name:
                piece = f"{piece} label {item.func}({col}) '{item.alias_name}'"
            compiled.append(piece)
        else:
            raise TypeError(f"Unsupported select item: {item!r}")
    return ", ".join(compiled)


def _compile_predicate(pred: Predicate, header_map: dict[str, str], dynamic: list[tuple[str, ConfigRef]]) -> str:
    left = _resolve_col(pred.left.name, header_map)
    right = pred.right
    if isinstance(right, ConfigRef):
        token = f"__CFG_{len(dynamic)}__"
        dynamic.append((token, right))
        return f"{left} {pred.op} {token}"
    if isinstance(right, str):
        return f"{left} {pred.op} '{right}'"
    if isinstance(right, bool):
        return f"{left} {pred.op} {'TRUE' if right else 'FALSE'}"
    return f"{left} {pred.op} {right}"


def _compile_order(orders: list[Order], header_map: dict[str, str]) -> str:
    out: list[str] = []
    for item in orders:
        col = header_map.get(item.name, item.name)
        out.append(col + (" desc" if item.descending else " asc"))
    return ", ".join(out)


def _inject_dynamic_tokens(query_text: str, dynamic: list[tuple[str, ConfigRef]]) -> str:
    if not dynamic:
        return quote_formula_string(query_text)
    pieces: list[str] = []
    cursor = 0
    for token, cfg_ref in dynamic:
        idx = query_text.index(token, cursor)
        static = query_text[cursor:idx]
        if static:
            pieces.append(quote_formula_string(static))
        pieces.append(_config_ref_expr(cfg_ref))
        cursor = idx + len(token)
    if query_text[cursor:]:
        pieces.append(quote_formula_string(query_text[cursor:]))
    return " & ".join(pieces)


def _config_ref_expr(cfg_ref: ConfigRef) -> str:
    if cfg_ref.type_name == "string":
        return f'"\'" & {cfg_ref.a1_ref} & "\'"'
    if cfg_ref.type_name == "date":
        return f'"date \'" & {cfg_ref.a1_ref} & "\'"'
    if cfg_ref.type_name == "boolean":
        return f'IF({cfg_ref.a1_ref}, "TRUE", "FALSE")'
    return cfg_ref.a1_ref


def _resolve_col(name: str, header_map: dict[str, str]) -> str:
    if name not in header_map:
        raise KeyError(f"Unknown column in header map: {name}")
    return header_map[name]
