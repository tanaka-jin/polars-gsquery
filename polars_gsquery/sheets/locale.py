from __future__ import annotations


def function_arg_delimiter(locale: str) -> str:
    if locale.startswith("ja"):
        return ";"
    return ","


def quote_formula_string(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
