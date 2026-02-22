from __future__ import annotations

from dataclasses import dataclass

from polars_gsquery.sheets.a1 import quote_sheet_name

VALID_TYPES = {"string", "number", "date", "boolean"}


@dataclass(frozen=True)
class ConfigRef:
    key: str
    type_name: str
    a1_ref: str


@dataclass
class Config:
    """Config map loaded from an existing Spreadsheet sheet."""

    sheet: str = "config"
    header_row: int = 1
    key_col: str = "A"
    type_col: str = "B"
    value_col: str = "C"

    def __post_init__(self) -> None:
        self._row_map: dict[str, tuple[str, int]] = {}

    def load_rows(self, rows: list[list[object]]) -> None:
        """Load config rows already read from Sheets (header + body)."""
        self._row_map.clear()
        for idx, row in enumerate(rows[1:], start=self.header_row + 1):
            if len(row) < 2:
                continue
            key = str(row[0]).strip()
            type_name = str(row[1]).strip()
            if not key:
                continue
            if key in self._row_map:
                raise ValueError(f"Duplicated config key: {key}")
            if type_name not in VALID_TYPES:
                raise ValueError(f"Unsupported config type: {type_name}")
            self._row_map[key] = (type_name, idx)

    def ref(self, key: str) -> ConfigRef:
        if key not in self._row_map:
            raise KeyError(f"Unknown config key: {key}")
        type_name, row_no = self._row_map[key]
        return ConfigRef(
            key=key,
            type_name=type_name,
            a1_ref=f"{quote_sheet_name(self.sheet)}!{self.value_col}{row_no}",
        )
