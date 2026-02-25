from __future__ import annotations

import re

_SIMPLE_SHEET_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def quote_sheet_name(name: str) -> str:
    if _SIMPLE_SHEET_NAME_RE.fullmatch(name):
        return name
    return "'" + name.replace("'", "''") + "'"


def column_index_to_a1(index: int) -> str:
    if index < 1:
        raise ValueError("index must be >= 1")

    out: list[str] = []
    n = index
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out.append(chr(ord("A") + rem))
    return "".join(reversed(out))


def column_a1_to_index(column: str) -> int:
    if not column or not column.isalpha():
        raise ValueError("column must be alphabetic")

    value = 0
    for ch in column.upper():
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return value
