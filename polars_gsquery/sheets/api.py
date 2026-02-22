from __future__ import annotations

from collections import defaultdict


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
