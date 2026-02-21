from polars_sheets_query import Config, SheetBook, q
from polars_sheets_query.sheets.api import SheetsAPI


def test_compile_formula_with_config_refs_ja_locale() -> None:
    api = SheetsAPI()
    api.set_header_fixture("mart", "A:Z", 1, ["country", "event_date", "sales"])

    cfg = Config(sheet="config")
    cfg.ensure_params(
        [
            ("country", "string", "JP"),
            ("start_date", "date", "2026-01-01"),
        ]
    )

    expr = (
        q.from_sheet("mart", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .where(q.col("country") == cfg.ref("country"))
        .where(q.col("event_date") >= cfg.ref("start_date"))
        .groupby(["country"])
        .orderby([q.desc("sales_sum")])
        .limit(50)
    )

    book = SheetBook("dummy", locale="ja_JP", api=api)
    formula = book.write_report("report_sales", expr, "A1")

    assert formula.startswith("=QUERY(mart!A:Z; ")
    assert '" & config!C2 & "\'"' in formula
    assert '"date \'" & config!C3 & "\'"' in formula
    assert "limit 50" in formula


def test_locale_en_uses_comma_separator() -> None:
    api = SheetsAPI()
    api.set_header_fixture("mart", "A:Z", 1, ["country", "sales"])
    expr = q.from_sheet("mart", header_rows=1, range_="A:Z").select(["country", q.sum("sales")]).groupby(["country"])

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)

    assert formula.startswith("=QUERY(mart!A:Z, ")
