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

    @classmethod
    def from_colab(cls, spreadsheet_id: str, locale: str = "ja_JP") -> "SheetBook":
        """Colab-first constructor.

        In production this should initialize Google auth/token clients,
        but MVP keeps API injectable and testable.
        """
        return cls(spreadsheet_id=spreadsheet_id, locale=locale)

    def load_config(self, cfg: Config, start_cell: str = "A1") -> None:
        assert self.api is not None
        rows = self.api.read_rows(cfg.sheet, start_cell=start_cell)
        cfg.load_rows(rows)

    def write_mart(self, df: object, sheet: str = "data", start_cell: str = "A1") -> None:
        """Write a single polars.DataFrame to Sheet as mart/data source."""
        assert self.api is not None
        columns = list(getattr(df, "columns"))
        values = [list(r) for r in df.iter_rows()]
        self.api.write_rows(sheet, start_cell, [columns, *values])
        self.api.set_header_fixture(sheet, "A:Z", 1, columns)

    def get_header_map(self, sheet: str, header_row: int, range_: str) -> dict[str, str]:
        assert self.api is not None
        headers = self.api.read_header(sheet, range_, header_row)
        return {name: f"Col{i}" for i, name in enumerate(headers, start=1)}

    def write_report(self, sheet: str, query_expr: QueryExpr, anchor_cell: str = "A1") -> str:
        assert self.api is not None
        self.api.ensure_sheet(sheet)
        header_map = self.get_header_map(query_expr.data_sheet, query_expr.header_rows, query_expr.range_)
        compiled = compile_formula(query_expr, header_map=header_map, locale=self.locale)
        self.api.write_cell(sheet, anchor_cell, compiled.formula)
        return compiled.formula
