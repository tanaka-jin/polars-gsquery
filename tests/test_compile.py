from polars_gsquery import Config, SheetBook, q
from polars_gsquery.sheets.api import SheetsAPI


def test_compile_formula_with_config_refs_ja_locale() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "event_date", "sales"])
    api.set_rows_fixture(
        "config",
        [["key", "type", "value"], ["country", "string", "JP"], ["start_date", "date", "2026-01-01"]],
    )

    cfg = Config(sheet="config")
    book = SheetBook("dummy", locale="ja_JP", api=api)
    book.load_config(cfg)

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .where(q.col("country") == cfg.ref("country"))
        .where(q.col("event_date") >= cfg.ref("start_date"))
        .groupby(["country"])
        .orderby([q.desc("sales_sum")])
        .limit(50)
    )

    formula = book.write_report("report_sales", expr, "A1")
    assert formula.startswith("=QUERY(data!A:Z; ")
    assert '" & config!C2 & "\'"' in formula
    assert '"date \'" & config!C3 & "\'"' in formula


def test_locale_en_uses_comma_separator() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])
    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales")])
        .groupby(["country"])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)
    assert formula.startswith("=QUERY(data!A:Z, ")
