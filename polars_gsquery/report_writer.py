from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .config_binding import bind_config_refs, has_deferred_config_refs
from .header_schema import infer_header_schema
from .qdsl.ast import QueryExpr
from .qdsl.compile import compile_formula
from .sheets.api import SupportsSheetsAPI


@dataclass
class ReportWriter:
    api: SupportsSheetsAPI
    locale: str

    def write_report(self, sheet: str, query_expr: QueryExpr, anchor_cell: str = "A1") -> str:
        self.api.ensure_sheet(sheet)

        resolved_expr = self._resolve_config(query_expr)
        schema = infer_header_schema(
            api=self.api,
            sheet=resolved_expr.data_sheet,
            header_row=resolved_expr.header_rows,
            range_=resolved_expr.range_,
        )

        compiled = compile_formula(
            resolved_expr.with_range(schema.range_),
            header_map=schema.header_map,
            locale=self.locale,
        )
        self.api.write_cell(sheet, anchor_cell, compiled.formula)
        return compiled.formula

    def _resolve_config(self, expr: QueryExpr, start_cell: str = "A1") -> QueryExpr:
        if expr.config_sheet is None or not has_deferred_config_refs(expr):
            return expr

        cfg = Config(sheet=expr.config_sheet)
        rows = self.api.read_rows(cfg.sheet, start_cell=start_cell)
        cfg.load_rows(rows)
        return bind_config_refs(expr, cfg)
