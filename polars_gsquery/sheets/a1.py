from __future__ import annotations

import re


_SIMPLE_SHEET_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def quote_sheet_name(name: str) -> str:
    if _SIMPLE_SHEET_NAME_RE.fullmatch(name):
        return name
    return "'" + name.replace("'", "''") + "'"
