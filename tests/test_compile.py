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
    assert formula.startswith("=QUERY(data!A:Z, ")
    assert 'SUBSTITUTE(config!C2, "\'", "\'\'")' in formula
    assert 'TEXT(config!C3, "yyyy-MM-dd")' in formula


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


def test_locale_de_uses_semicolon_separator() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])
    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales")])
        .groupby(["country"])
    )

    book = SheetBook("dummy", locale="de_DE", api=api)
    formula = book.write_report("report_sales", expr)
    assert formula.startswith("=QUERY(data!A:Z; ")


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


def test_compile_escapes_string_literal_and_alias_quotes() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["publisher", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["publisher", q.sum("sales").alias("sales_sum's")])
        .where(q.col("publisher") == "O'Reilly")
        .groupby(["publisher"])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)

    assert "where A = 'O''Reilly'" in formula
    assert "label sum(B) 'sales_sum''s'" in formula


def test_compile_quotes_sheet_names_in_query_a1_range() -> None:
    api = SheetsAPI()
    api.set_header_fixture("raw data", "A:Z", 1, ["country", "sales"])
    api.set_rows_fixture("Bob's sheet", [["key", "type", "value"], ["country", "string", "O'Reilly"]])

    cfg = Config(sheet="Bob's sheet")
    book = SheetBook("dummy", locale="en_US", api=api)
    book.load_config(cfg)

    expr = (
        q.from_sheet(data_sheet="raw data", config_sheet="Bob's sheet", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales")])
        .where(q.col("country") == cfg.ref("country"))
        .groupby(["country"])
    )

    formula = book.write_report("report", expr)
    assert formula.startswith("=QUERY('raw data'!A:Z, ")
    assert "SUBSTITUTE('Bob''s sheet'!C2, \"'\", \"''\")" in formula


def test_query_expr_is_immutable_when_reused() -> None:
    base = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(["country"])

    q1 = base.where(q.col("country") == "JP")
    q2 = base.where(q.col("country") == "US")

    assert len(base.predicates) == 0
    assert len(q1.predicates) == 1
    assert len(q2.predicates) == 1
    assert q1.predicates[0].right == "JP"
    assert q2.predicates[0].right == "US"


def test_limit_negative_raises_value_error() -> None:
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z")

    with pytest.raises(ValueError):
        expr.limit(-1)


def test_orderby_asc_is_supported() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(["country"]).orderby([q.asc("country")])

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)
    assert "order by A asc" in formula


def test_select_omitted_defaults_to_star() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z")

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)
    assert '"select *"' in formula


def test_select_empty_list_defaults_to_star() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select([])

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)
    assert '"select *"' in formula


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, "where A = 1"),
        (1.5, "where A = 1.5"),
        (True, "where A = TRUE"),
        (False, "where A = FALSE"),
    ],
)
def test_where_numeric_and_bool_literals_are_compiled(value: object, expected: str) -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["value"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(q.col("value") == value)

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert expected in formula


def test_orderby_coln_reference_is_supported() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(["country"]).orderby([q.desc("Col2")])

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "order by Col2 desc" in formula


def test_orderby_prefers_alias_over_header_name() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["sales_sum", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z")
        .select(["sales_sum", q.sum("sales").alias("sales_sum")])
        .orderby([q.desc("sales_sum")])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "order by sum(B) desc" in formula


def test_unknown_select_column_raises_keyerror_with_context() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(["missing_col"])
    book = SheetBook("dummy", locale="en_US", api=api)

    with pytest.raises(KeyError, match="Unknown column in header map"):
        book.write_report("report", expr)


def test_unknown_config_reference_raises_keyerror_with_context() -> None:
    cfg = Config(sheet="config")
    cfg.load_rows([["key", "type", "value"], ["country", "string", "JP"]])

    with pytest.raises(KeyError, match="Unknown config key"):
        cfg.ref("missing")


def test_where_accepts_raw_query_string() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where("B > 100")

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where B > 100" in formula


def test_clause_order_is_independent_from_call_order() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(q.col("sales") > 100).select(["country"])

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert '"select A\nwhere B > 100"' in formula
