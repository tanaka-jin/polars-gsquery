from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .qdsl.ast import QueryExpr
from .qdsl.compile import compile_formula
from .sheets.api import GoogleSheetsAPI, SheetsAPI, SupportsSheetsAPI


@dataclass
class SheetBook:
    spreadsheet_id: str
    creds: object | None = None
    locale: str = "en_US"
    api: SupportsSheetsAPI | None = None

    def __post_init__(self) -> None:
        if self.api is None:
            self.api = SheetsAPI()

    @classmethod
    def from_colab(cls, spreadsheet_id: str, locale: str = "ja_JP") -> "SheetBook":
        """Colab-first constructor with Google auth + Sheets clients."""
        from google.auth import default
        from google.colab import auth
        from googleapiclient.discovery import build
        import gspread

        auth.authenticate_user()
        creds, _ = default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gspread_client = gspread.authorize(creds)
        values_service = build("sheets", "v4", credentials=creds).spreadsheets().values()

        api = GoogleSheetsAPI(
            spreadsheet_id=spreadsheet_id,
            gspread_client=gspread_client,
            values_service=values_service,
        )
        return cls(spreadsheet_id=spreadsheet_id, creds=creds, locale=locale, api=api)

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
        if isinstance(self.api, SheetsAPI):
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
