import pytest

from polars_gsquery import SheetBook, q
from polars_gsquery.sheets.api import SheetsAPI


class FakeDF:
    columns = ["a", "b"]

    def iter_rows(self):
        return [(1, 2), (3, 4)]


def test_write_mart_stores_rows_and_header() -> None:
    api = SheetsAPI()
    book = SheetBook("dummy", api=api)
    book.write_mart(FakeDF(), sheet="data")
    assert api.read_rows("data") == [["a", "b"], [1, 2], [3, 4]]
    assert api.read_header("data", "A:Z", 1) == ["a", "b"]


def test_get_header_map_uses_coln_column_names() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", "b", "z", "aa"])
    book = SheetBook("dummy", api=api)

    assert book.get_header_map("data", 1, "A:Z") == {"a": "Col1", "b": "Col2", "z": "Col3", "aa": "Col4"}


def test_get_header_map_rejects_empty_header_name() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", " "])
    book = SheetBook("dummy", api=api)

    with pytest.raises(ValueError, match="empty column name"):
        book.get_header_map("data", 1, "A:Z")


def test_get_header_map_rejects_duplicate_header_name() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", "a"])
    book = SheetBook("dummy", api=api)

    with pytest.raises(ValueError, match="duplicate column name"):
        book.get_header_map("data", 1, "A:Z")


def test_get_header_map_errors_when_header_is_missing() -> None:
    api = SheetsAPI()
    book = SheetBook("dummy", api=api)

    with pytest.raises(ValueError, match="Failed to read header row"):
        book.get_header_map("data", 1, "A:Z")


def test_write_mart_rejects_ragged_rows() -> None:
    class RaggedDF:
        columns = ["a", "b"]

        def iter_rows(self):
            return [(1,), (2, 3)]

    api = SheetsAPI()
    book = SheetBook("dummy", api=api)

    with pytest.raises(ValueError, match="ragged rows"):
        book.write_mart(RaggedDF(), sheet="data")


def test_write_mart_accepts_generator_iter_rows() -> None:
    class GeneratorDF:
        columns = ["a", "b"]

        def iter_rows(self):
            yield (1, 2)
            yield (3, 4)

    api = SheetsAPI()
    book = SheetBook("dummy", api=api)

    book.write_mart(GeneratorDF(), sheet="data")
    assert api.read_rows("data") == [["a", "b"], [1, 2], [3, 4]]


def test_write_mart_empty_rows_with_columns_writes_header_only() -> None:
    class EmptyRowsDF:
        columns = ["a", "b"]

        def iter_rows(self):
            return iter(())

    api = SheetsAPI()
    book = SheetBook("dummy", api=api)

    book.write_mart(EmptyRowsDF(), sheet="data")
    assert api.read_rows("data") == [["a", "b"]]


def test_write_mart_empty_columns_and_rows_is_allowed() -> None:
    class EmptyDF:
        columns = []

        def iter_rows(self):
            return iter(())

    api = SheetsAPI()
    book = SheetBook("dummy", api=api)

    book.write_mart(EmptyDF(), sheet="data")
    assert api.read_rows("data") == [[]]


def test_write_mart_then_get_header_map_works_without_explicit_header_fixture() -> None:
    api = SheetsAPI()
    book = SheetBook("dummy", api=api)

    book.write_mart(FakeDF(), sheet="data")

    assert book.get_header_map("data", 1, "A:Z") == {"a": "Col1", "b": "Col2"}


def test_write_mart_then_write_report_works_without_explicit_header_fixture() -> None:
    api = SheetsAPI()
    book = SheetBook("dummy", api=api)
    book.write_mart(FakeDF(), sheet="data")

    expr = q.from_sheet(data_sheet="data").select(["a"])

    formula = book.write_report("report", expr)
    assert formula.startswith("=QUERY(data!A:B,")


def test_write_mart_ragged_rows_do_not_write_partial_data() -> None:
    class RaggedDF:
        columns = ["a", "b"]

        def iter_rows(self):
            return [(1, 2), (3,)]

    api = SheetsAPI()
    book = SheetBook("dummy", api=api)

    with pytest.raises(ValueError, match="ragged rows"):
        book.write_mart(RaggedDF(), sheet="data")

    with pytest.raises(KeyError):
        api.read_rows("data")


def test_write_report_auto_loads_config_when_config_sheet_is_set() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country"])
    api.write_rows("params", "A1", [["key", "type", "value"], ["country", "string", "JP"]])

    book = SheetBook("dummy", api=api)
    expr = q.from_sheet(data_sheet="data", config_sheet="params").where(q.col("country") == q.cfg("country"))

    formula = book.write_report("report", expr)
    assert "SUBSTITUTE(params!C2" in formula


def test_write_report_uses_default_config_sheet_for_load_config() -> None:
    api = SheetsAPI()
    api.write_rows("params", "A1", [["key", "type", "value"], ["country", "string", "JP"]])
    book = SheetBook("dummy", api=api, config_sheet="params")

    cfg = book.load_config()
    assert cfg.ref("country").a1_ref == "params!C2"


def test_write_report_infers_range_from_header_when_not_specified() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    book = SheetBook("dummy", locale="en_US", api=api)
    expr = q.from_sheet(data_sheet="data").select(["country"])

    formula = book.write_report("report", expr)
    assert "=QUERY(data!A:B," in formula
