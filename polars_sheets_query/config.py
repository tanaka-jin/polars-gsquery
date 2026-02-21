from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

VALID_TYPES = {"string", "number", "date", "boolean"}


@dataclass(frozen=True)
class ConfigRef:
    key: str
    type_name: str
    a1_ref: str


@dataclass
class Config:
    sheet: str = "config"
    header_row: int = 1
    key_col: str = "A"
    type_col: str = "B"
    value_col: str = "C"
    _row_map: dict[str, tuple[str, int]] = field(default_factory=dict)
    _rows: list[list[object]] = field(default_factory=list)

    def ensure_params(self, params: Iterable[tuple[str, str, object]]) -> list[list[object]]:
        seen: set[str] = set()
        rows: list[list[object]] = [["key", "type", "value", "note"]]
        row_no = self.header_row + 1
        for key, type_name, value in params:
            if key in seen:
                raise ValueError(f"Duplicated config key: {key}")
            if type_name not in VALID_TYPES:
                raise ValueError(f"Unsupported config type: {type_name}")
            seen.add(key)
            self._row_map[key] = (type_name, row_no)
            rows.append([key, type_name, value, ""])
            row_no += 1
        self._rows = rows
        return rows

    def rows(self) -> list[list[object]]:
        if not self._rows:
            return [["key", "type", "value", "note"]]
        return self._rows

    def ref(self, key: str) -> ConfigRef:
        if key not in self._row_map:
            raise KeyError(f"Unknown config key: {key}")
        type_name, row_no = self._row_map[key]
        return ConfigRef(key=key, type_name=type_name, a1_ref=f"{self.sheet}!{self.value_col}{row_no}")
