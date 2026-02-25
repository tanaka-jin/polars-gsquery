from __future__ import annotations

from typing import Iterable, Protocol


class SupportsDataFrame(Protocol):
    columns: list[str]

    def iter_rows(self) -> Iterable[tuple[object, ...]]: ...


def rows_from_frame(df: SupportsDataFrame) -> list[list[object]]:
    columns = [str(c) for c in df.columns]
    values = [list(row) for row in df.iter_rows()]
    return [columns, *values]


def validate_rectangular_rows(rows: list[list[object]]) -> None:
    if not rows:
        raise ValueError("write_mart produced no rows")

    header_width = len(rows[0])
    for i, row in enumerate(rows, start=1):
        if len(row) != header_width:
            raise ValueError(
                f"write_mart wrote ragged rows: row {i} has {len(row)} columns but header has {header_width}"
            )
