from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .qdsl.ast import QueryExpr
from .qdsl.compile import compile_formula
from .sheets.api import SheetsAPI


@dataclass
class SheetBook:
    spreadsheet_id: str
    creds: object | None = None
    locale: str = "en_US"
    api: SheetsAPI | None = None

    def __post_init__(self) -> None:
        if self.api is None:
            self.api = SheetsAPI()

    def apply_config(self, cfg: Config) -> None:
        assert self.api is not None
        self.api.ensure_sheet(cfg.sheet)
        self.api.write_rows(cfg.sheet, f"{cfg.key_col}{cfg.header_row}", cfg.rows())

    def get_header_map(self, sheet: str, header_row: int, range_: str) -> dict[str, str]:
        assert self.api is not None
        headers = self.api.read_header(sheet, range_, header_row)
        return {name: f"Col{i}" for i, name in enumerate(headers, start=1)}

    def write_report(self, sheet: str, query_expr: QueryExpr, anchor_cell: str = "A1") -> str:
        assert self.api is not None
        self.api.ensure_sheet(sheet)
        header_map = self.get_header_map(query_expr.source_sheet, query_expr.header_rows, query_expr.range_)
        compiled = compile_formula(query_expr, header_map=header_map, locale=self.locale)
        self.api.write_cell(sheet, anchor_cell, compiled.formula)
        return compiled.formula
