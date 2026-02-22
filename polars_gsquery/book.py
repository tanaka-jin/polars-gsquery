from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .config import Config
from .qdsl.ast import QueryExpr
from .qdsl.compile import compile_formula
from .sheets.api import GoogleSheetsAPI, SheetsAPI, SupportsSheetsAPI


class SupportsDataFrame(Protocol):
    columns: list[str]

    def iter_rows(self) -> Iterable[tuple[object, ...]]: ...


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
        rows = self._require_api().read_rows(cfg.sheet, start_cell=start_cell)
        cfg.load_rows(rows)

    def write_mart(self, df: SupportsDataFrame, sheet: str = "data", start_cell: str = "A1") -> None:
        """Write a single polars.DataFrame to Sheet as mart/data source."""
        api = self._require_api()
        rows = _rows_from_frame(df)
        api.write_rows(sheet, start_cell, rows)
        if isinstance(api, SheetsAPI):
            api.set_header_fixture(sheet, "A:Z", 1, rows[0])

    def get_header_map(self, sheet: str, header_row: int, range_: str) -> dict[str, str]:
        headers = self._require_api().read_header(sheet, range_, header_row)
        return {name: _column_index_to_a1(i) for i, name in enumerate(headers, start=1)}

    def write_report(self, sheet: str, query_expr: QueryExpr, anchor_cell: str = "A1") -> str:
        api = self._require_api()
        api.ensure_sheet(sheet)
        header_map = self.get_header_map(query_expr.data_sheet, query_expr.header_rows, query_expr.range_)
        compiled = compile_formula(query_expr, header_map=header_map, locale=self.locale)
        api.write_cell(sheet, anchor_cell, compiled.formula)
        return compiled.formula

    def _require_api(self) -> SupportsSheetsAPI:
        if self.api is None:
            raise RuntimeError("Sheets API is not initialized")
        return self.api


def _rows_from_frame(df: SupportsDataFrame) -> list[list[object]]:
    columns = [str(c) for c in df.columns]
    values = [list(row) for row in df.iter_rows()]
    return [columns, *values]


def _column_index_to_a1(index: int) -> str:
    if index < 1:
        raise ValueError("index must be >= 1")

    out: list[str] = []
    n = index
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out.append(chr(ord("A") + rem))
    return "".join(reversed(out))
