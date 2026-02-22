from __future__ import annotations

from collections import defaultdict
from typing import Protocol


def _header_row_range(range_: str, header_row: int) -> str:
    start_col, end_col = range_.split(":", maxsplit=1)
    return f"{start_col}{header_row}:{end_col}{header_row}"


class SupportsSheetsAPI(Protocol):
    def ensure_sheet(self, name: str) -> None: ...

    def write_cell(self, sheet: str, a1: str, value: object) -> None: ...

    def write_rows(self, sheet: str, start_cell: str, rows: list[list[object]]) -> None: ...

    def read_rows(self, sheet: str, start_cell: str = "A1") -> list[list[object]]: ...

    def read_header(self, sheet: str, range_: str, header_row: int) -> list[str]: ...


class SheetsAPI:
    """Tiny in-memory adapter for MVP and tests."""

    def __init__(self) -> None:
        self._sheets: dict[str, dict[str, object]] = defaultdict(dict)

    def ensure_sheet(self, name: str) -> None:
        self._sheets.setdefault(name, {})

    def write_cell(self, sheet: str, a1: str, value: object) -> None:
        self.ensure_sheet(sheet)
        self._sheets[sheet][a1] = value

    def write_rows(self, sheet: str, start_cell: str, rows: list[list[object]]) -> None:
        self.ensure_sheet(sheet)
        self._sheets[sheet][f"ROWS:{start_cell}"] = rows

    def read_rows(self, sheet: str, start_cell: str = "A1") -> list[list[object]]:
        value = self._sheets.get(sheet, {}).get(f"ROWS:{start_cell}")
        if not isinstance(value, list):
            raise KeyError(f"Missing rows fixture for {sheet}!{start_cell}")
        return value

    def read_header(self, sheet: str, range_: str, header_row: int) -> list[str]:
        key = f"HEADER:{range_}:{header_row}"
        value = self._sheets.get(sheet, {}).get(key)
        if not isinstance(value, list):
            raise KeyError(f"Missing header fixture for {sheet}!{range_} row={header_row}")
        return value

    def set_header_fixture(self, sheet: str, range_: str, header_row: int, headers: list[str]) -> None:
        self.ensure_sheet(sheet)
        self._sheets[sheet][f"HEADER:{range_}:{header_row}"] = headers

    def set_rows_fixture(self, sheet: str, rows: list[list[object]], start_cell: str = "A1") -> None:
        self.ensure_sheet(sheet)
        self._sheets[sheet][f"ROWS:{start_cell}"] = rows


class GoogleSheetsAPI:
    """Google Sheets adapter using gspread and googleapiclient."""

    def __init__(self, spreadsheet_id: str, gspread_client: object, values_service: object) -> None:
        self.spreadsheet_id = spreadsheet_id
        self._gspread_client = gspread_client
        self._values_service = values_service

    def ensure_sheet(self, name: str) -> None:
        workbook = self._gspread_client.open_by_key(self.spreadsheet_id)
        try:
            workbook.worksheet(name)
        except Exception:
            workbook.add_worksheet(title=name, rows=1000, cols=26)

    def write_cell(self, sheet: str, a1: str, value: object) -> None:
        self.ensure_sheet(sheet)
        self._values_service.update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet}!{a1}",
            valueInputOption="USER_ENTERED",
            body={"values": [[value]]},
        ).execute()

    def write_rows(self, sheet: str, start_cell: str, rows: list[list[object]]) -> None:
        self.ensure_sheet(sheet)
        self._values_service.update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet}!{start_cell}",
            valueInputOption="USER_ENTERED",
            body={"values": rows},
        ).execute()

    def read_rows(self, sheet: str, start_cell: str = "A1") -> list[list[object]]:
        resp = self._values_service.get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet}!{start_cell}:ZZ",
        ).execute()
        values = resp.get("values", [])
        return [list(r) for r in values]

    def read_header(self, sheet: str, range_: str, header_row: int) -> list[str]:
        resp = self._values_service.get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet}!{_header_row_range(range_, header_row)}",
        ).execute()
        rows = resp.get("values", [])
        if not rows:
            return []
        return [str(v) for v in rows[0]]
