from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .config_binding import bind_config_refs, has_deferred_config_refs
from .frame_rows import SupportsDataFrame, rows_from_frame, validate_rectangular_rows
from .header_schema import read_header_map
from .qdsl.ast import QueryExpr
from .report_writer import ReportWriter
from .sheets.api import GoogleSheetsAPI, SheetsAPI, SupportsSheetsAPI


@dataclass
class SheetBook:
    spreadsheet_id: str
    creds: object | None = None
    locale: str = "en_US"
    config_sheet: str = "config"
    api: SupportsSheetsAPI | None = None

    def __post_init__(self) -> None:
        if self.api is None:
            self.api = SheetsAPI()

    @classmethod
    def from_colab(cls, spreadsheet_id: str, locale: str = "ja_JP") -> "SheetBook":
        """Colab-first constructor with Google auth + Sheets clients."""
        import gspread
        from google.auth import default
        from google.colab import auth
        from googleapiclient.discovery import build

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

    def load_config(self, cfg: Config | None = None, start_cell: str = "A1") -> Config:
        target = cfg if cfg is not None else Config(sheet=self.config_sheet)
        rows = self._require_api().read_rows(target.sheet, start_cell=start_cell)
        target.load_rows(rows)
        return target

    def ensure_config_loaded(self, expr: QueryExpr, start_cell: str = "A1") -> QueryExpr:
        if expr.config_sheet is None or not has_deferred_config_refs(expr):
            return expr

        cfg = Config(sheet=expr.config_sheet)
        self.load_config(cfg, start_cell=start_cell)
        return bind_config_refs(expr, cfg)

    def write_mart(self, df: SupportsDataFrame, sheet: str = "data", start_cell: str = "A1") -> None:
        """Write a single polars.DataFrame to Sheet as mart/data source."""
        api = self._require_api()
        rows = rows_from_frame(df)
        validate_rectangular_rows(rows)
        api.write_rows(sheet, start_cell, rows)

    def get_header_map(self, sheet: str, header_row: int, range_: str) -> dict[str, str]:
        return read_header_map(self._require_api(), sheet=sheet, header_row=header_row, range_=range_)

    def write_report(self, sheet: str, query_expr: QueryExpr, anchor_cell: str = "A1") -> str:
        writer = ReportWriter(api=self._require_api(), locale=self.locale)
        return writer.write_report(sheet=sheet, query_expr=query_expr, anchor_cell=anchor_cell)

    def _require_api(self) -> SupportsSheetsAPI:
        if self.api is None:
            raise RuntimeError("Sheets API is not initialized")
        return self.api
