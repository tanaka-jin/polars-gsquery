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
