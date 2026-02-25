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
        .group_by(["country"])
        .sort("sales_sum", descending=True)
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


def test_compile_formula_skips_string_config_predicate_when_cell_is_blank() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country"])
    api.set_rows_fixture("config", [["key", "type", "value"], ["country", "string", ""]])

    cfg = Config(sheet="config")
    book = SheetBook("dummy", locale="en_US", api=api)
    book.load_config(cfg)

    expr = q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z").where(
        q.col("country") == cfg.ref("country")
    )

    formula = book.write_report("report", expr)
    assert 'IF(LEN(TRIM(TO_TEXT(config!C2)))=0, "1=1", "Col1 = " &' in formula


def test_compile_formula_skips_number_config_predicate_when_cell_is_blank() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["sales"])
    api.set_rows_fixture("config", [["key", "type", "value"], ["min_sales", "number", ""]])

    cfg = Config(sheet="config")
    book = SheetBook("dummy", locale="en_US", api=api)
    book.load_config(cfg)

    expr = q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z").where(
        q.col("sales") >= cfg.ref("min_sales")
    )

    formula = book.write_report("report", expr)
    assert 'IF(LEN(TRIM(TO_TEXT(config!C2)))=0, "1=1", "Col1 >= " & config!C2)' in formula


def test_locale_en_uses_comma_separator() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])
    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales")])
        .group_by(["country"])
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
        .group_by(["country"])
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
        .group_by(["country"])
        .limit(10)
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)

    assert "\nwhere" not in formula
    assert "\n" in formula
    assert "label sum(Col2) 'sales_sum'" in formula


def test_sort_alias_name_is_supported() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .group_by(["country"])
        .sort("sales_sum", descending=True)
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)
    assert "order by sum(Col2) desc" in formula


def test_sort_a1_column_name_is_rejected() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .group_by(["country"])
        .sort("B", descending=True)
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    with pytest.raises(KeyError, match="Unknown order key"):
        book.write_report("report_sales", expr)


def test_sort_unknown_column_raises_keyerror() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
        .select(["country", q.sum("sales").alias("sales_sum")])
        .group_by(["country"])
        .sort("not_exists", descending=True)
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
        .group_by(["publisher"])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)

    assert "where Col1 = 'O''Reilly'" in formula
    assert "label sum(Col2) 'sales_sum''s'" in formula


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
        .group_by(["country"])
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


def test_sort_accepts_single_string_input() -> None:
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").sort("country")

    assert expr.order == (("country", False),)


def test_sort_rejects_non_str_items() -> None:
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z")

    with pytest.raises(TypeError, match="item must be str"):
        expr.sort([123])


def test_old_method_names_are_removed() -> None:
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z")

    assert not hasattr(expr, "groupby")
    assert not hasattr(expr, "orderby")


def test_sort_asc_is_supported() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(["country"]).sort("country")

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report_sales", expr)
    assert "order by Col1 asc" in formula


def test_select_and_group_by_accept_single_string() -> None:
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select("country").group_by("country")

    assert expr.selected == ("country",)
    assert expr.group_keys == ("country",)


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
        (1, "where Col1 = 1"),
        (1.5, "where Col1 = 1.5"),
        (True, "where Col1 = TRUE"),
        (False, "where Col1 = FALSE"),
    ],
)
def test_where_numeric_and_bool_literals_are_compiled(value: object, expected: str) -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["value"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(q.col("value") == value)

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert expected in formula


@pytest.mark.parametrize("name", ["Col2", "col2"])
def test_sort_coln_reference_is_rejected_with_policy_message(name: str) -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(["country"]).sort(name, descending=True)

    book = SheetBook("dummy", locale="en_US", api=api)
    with pytest.raises(KeyError, match="ColN style column references are not supported"):
        book.write_report("report", expr)


def test_sort_prefers_alias_over_header_name() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["sales_sum", "sales"])

    expr = (
        q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z")
        .select(["sales_sum", q.sum("sales").alias("sales_sum")])
        .sort("sales_sum", descending=True)
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "order by sum(Col2) desc" in formula


def test_select_coln_reference_is_rejected_with_policy_message() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(["Col2"])
    book = SheetBook("dummy", locale="en_US", api=api)

    with pytest.raises(KeyError, match="ColN style column references are not supported"):
        book.write_report("report", expr)


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
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where("Col2 > 100")

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where Col2 > 100" in formula


def test_select_supports_raw_expr_with_qcol_placeholders() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["A", "B"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(
        [q.raw("{left} - {right}", left=q.col("A"), right=q.col("B"))]
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert '"select Col1 - Col2"' in formula


def test_where_raw_supports_qcol_placeholders() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(
        q.raw("{sales_col} > 100 and {country_col} = 'JP'", sales_col=q.col("sales"), country_col=q.col("country"))
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where Col2 > 100 and Col1 = 'JP'" in formula


def test_where_raw_with_non_col_placeholder_raises_type_error() -> None:
    with pytest.raises(TypeError, match=r"placeholder must be q\.col"):
        q.raw("{sales} > 100", sales="sales")


def test_clause_order_is_independent_from_call_order() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(q.col("sales") > 100).select(["country"])

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert '"select Col1\nwhere Col2 > 100"' in formula


def test_agg_accepts_qcol_argument() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["sales"])
    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select([q.sum(q.col("sales"))])

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert '"select sum(Col1)"' in formula


def test_select_supports_avg_without_group_by() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["price"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select([q.avg("price")])

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert '"select avg(Col1)"' in formula


def test_select_supports_avg_with_group_by() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "price"])

    expr = (
        q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z")
        .select(["country", q.avg("price")])
        .group_by(["country"])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert '"select Col1, avg(Col2)\ngroup by Col1"' in formula


def test_select_supports_min_max_with_group_by() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "price"])

    expr = (
        q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z")
        .select(["country", q.min("price"), q.max("price")])
        .group_by(["country"])
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert '"select Col1, min(Col2), max(Col2)\ngroup by Col1"' in formula


def test_select_supports_new_aggs_with_alias_and_label() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["price"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(
        [q.avg("price").alias("avg_price"), q.min("price").alias("min_price"), q.max("price").alias("max_price")]
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "label avg(Col1) 'avg_price', min(Col1) 'min_price', max(Col1) 'max_price'" in formula


def test_select_supports_multiple_aggregations_in_single_select() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["price"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").select(
        [q.sum("price"), q.count("price"), q.avg("price"), q.min("price"), q.max("price")]
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert '"select sum(Col1), count(Col1), avg(Col1), min(Col1), max(Col1)"' in formula


def test_where_supports_boolean_or_expression() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(
        (q.col("country") == "JP") | (q.col("country") == "US")
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where (Col1 = 'JP' or Col1 = 'US')" in formula


def test_where_supports_boolean_and_expression_operator() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", "b"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where((q.col("a") == 1) & (q.col("b") == 2))

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where (Col1 = 1 and Col2 = 2)" in formula


def test_where_supports_mixed_and_or_with_explicit_parentheses() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", "b", "c"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(
        ((q.col("a") == 1) | (q.col("b") == 2)) & (q.col("c") == 3)
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where ((Col1 = 1 or Col2 = 2) and Col3 = 3)" in formula


def test_where_supports_nested_boolean_grouping_variants() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", "b", "c"])

    expr1 = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(
        ((q.col("a") == 1) | (q.col("b") == 2)) & (q.col("c") == 3)
    )
    expr2 = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(
        (q.col("a") == 1) & ((q.col("b") == 2) | (q.col("c") == 3))
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula1 = book.write_report("report1", expr1)
    formula2 = book.write_report("report2", expr2)
    assert "where ((Col1 = 1 or Col2 = 2) and Col3 = 3)" in formula1
    assert "where (Col1 = 1 and (Col2 = 2 or Col3 = 3))" in formula2


def test_where_supports_boolean_expression_with_string_comparison() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "status"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(
        (q.col("country") == "JP") & (q.col("status") != "inactive")
    )

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where (Col1 = 'JP' and Col2 != 'inactive')" in formula


def test_where_supports_boolean_expression_with_numeric_comparison() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", "b"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where((q.col("a") > 10) | (q.col("b") <= 20))

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where (Col1 > 10 or Col2 <= 20)" in formula


def test_where_multiple_arguments_keep_implicit_and_behavior() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", "b"])

    expr = q.from_sheet(data_sheet="data", header_rows=1, range_="A:Z").where(q.col("a") == 1, q.col("b") == 2)

    book = SheetBook("dummy", locale="en_US", api=api)
    formula = book.write_report("report", expr)
    assert "where Col1 = 1 and Col2 = 2" in formula
