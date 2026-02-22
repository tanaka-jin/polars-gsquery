from polars_gsquery import SheetBook
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


def test_get_header_map_uses_a1_column_letters() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["a", "b", "z", "aa"])
    book = SheetBook("dummy", api=api)

    assert book.get_header_map("data", 1, "A:Z") == {"a": "A", "b": "B", "z": "C", "aa": "D"}
