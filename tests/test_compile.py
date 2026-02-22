import pytest
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
    assert 'TEXT(config!C3; "yyyy-MM-dd")' in formula




def test_compile_formula_with_config_date_ref_en_locale_uses_text_format() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["event_date"])
    api.set_rows_fixture("config", [["key", "type", "value"], ["start_date", "date", "2026-01-01"]])

    cfg = Config(sheet="config")
    book = SheetBook("dummy", locale="en_US", api=api)
    book.load_config(cfg)

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["event_date"])
        .where(q.col("event_date") >= cfg.ref("start_date"))
    )

    formula = book.write_report("report_sales", expr, "A1")
    assert '"date \'" & TEXT(config!C2, "yyyy-MM-dd") & "\'"' in formula

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


def test_compiled_query_uses_multiline_and_label_clause() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .groupby(["country"])
        .limit(10)
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)

    assert "\nwhere" not in formula
    assert "\n" in formula
    assert "label sum(B) 'sales_sum'" in formula


def test_orderby_alias_name_is_supported() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .groupby(["country"])
        .orderby([q.desc("sales_sum")])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)
    assert "order by sum(B) desc" in formula


def test_orderby_a1_column_name_is_supported() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .groupby(["country"])
        .orderby([q.desc("B")])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)
    assert "order by B desc" in formula


def test_orderby_unknown_column_raises_keyerror() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .groupby(["country"])
        .orderby([q.desc("not_exists")])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    with pytest.raises(KeyError):
        book.write_report("report_sales", expr)
