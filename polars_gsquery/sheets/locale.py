from __future__ import annotations


SEMICOLON_LANGS = {
    "bg", "cs", "da", "de", "el", "es", "et", "fi", "fr", "hr", "hu", "it",
    "lt", "lv", "nl", "no", "pl", "pt", "ro", "ru", "sk", "sl", "sv", "tr", "uk",
}


def function_arg_delimiter(locale: str) -> str:
    """Return Sheets formula argument delimiter for the locale.

    Most dot-decimal locales (e.g. en_US, ja_JP) use `,`.
    Many comma-decimal locales use `;` to avoid ambiguity.
    """
    language = (locale or "").split("_", 1)[0].lower()
    if language in SEMICOLON_LANGS:
        return ";"
    return ","


def quote_formula_string(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
