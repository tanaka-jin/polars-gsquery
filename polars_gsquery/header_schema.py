from __future__ import annotations

from dataclasses import dataclass

from .sheets.a1 import column_index_to_a1
from .sheets.api import SupportsSheetsAPI


@dataclass(frozen=True)
class HeaderSchema:
    range_: str
    header_map: dict[str, str]


def read_header_map(api: SupportsSheetsAPI, sheet: str, header_row: int, range_: str) -> dict[str, str]:
    try:
        headers = api.read_header(sheet, range_, header_row)
    except KeyError as exc:
        raise ValueError(f"Failed to read header row: {sheet}!{range_} row={header_row}") from exc

    if not headers:
        raise ValueError(f"Header row is empty or missing: {sheet}!{range_} row={header_row}")

    header_map: dict[str, str] = {}
    for i, raw_name in enumerate(headers, start=1):
        name = str(raw_name).strip()
        if not name:
            raise ValueError(f"Header contains an empty column name at {sheet}!{column_index_to_a1(i)}{header_row}")
        if name in header_map:
            raise ValueError(
                f"Header contains duplicate column name: {name!r} at {sheet}!{column_index_to_a1(i)}{header_row}"
            )
        header_map[name] = _column_index_to_query_col(i)
    return header_map


def infer_header_schema(api: SupportsSheetsAPI, sheet: str, header_row: int, range_: str | None) -> HeaderSchema:
    header_range = range_ if range_ is not None else "A:Z"
    header_map = read_header_map(api, sheet, header_row, header_range)

    resolved_range = range_ if range_ is not None else f"A:{column_index_to_a1(len(header_map))}"
    return HeaderSchema(range_=resolved_range, header_map=header_map)


def _column_index_to_query_col(index: int) -> str:
    if index < 1:
        raise ValueError("index must be >= 1")
    return f"Col{index}"
