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
        key_idx = _column_to_index(self.key_col)
        type_idx = _column_to_index(self.type_col)

        for idx, row in enumerate(rows[1:], start=self.header_row + 1):
            if max(key_idx, type_idx) >= len(row):
                continue
            key = str(row[key_idx]).strip()
            type_name = str(row[type_idx]).strip()
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


def _column_to_index(col: str) -> int:
    normalized = col.strip().upper()
    if not normalized or any(not ("A" <= ch <= "Z") for ch in normalized):
        raise ValueError(f"Invalid column label: {col!r}")

    out = 0
    for ch in normalized:
        out = out * 26 + (ord(ch) - ord("A") + 1)
    return out - 1
