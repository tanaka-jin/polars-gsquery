from __future__ import annotations

from types import SimpleNamespace

from polars_gsquery.book import SheetBook
from polars_gsquery.sheets.api import GoogleSheetsAPI


class _Exec:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeValuesService:
    def __init__(self):
        self.updated = []
        self.get_payloads = {}

    def update(self, **kwargs):
        self.updated.append(kwargs)
        return _Exec({})

    def get(self, **kwargs):
        key = kwargs["range"]
        return _Exec(self.get_payloads.get(key, {}))


class FakeWorkbook:
    def __init__(self):
        self.tabs = set()

    def worksheet(self, name: str):
        if name not in self.tabs:
            raise RuntimeError("missing")
        return name

    def add_worksheet(self, title: str, rows: int, cols: int):
        self.tabs.add(title)


class FakeGspreadClient:
    def __init__(self, workbook):
        self.workbook = workbook

    def open_by_key(self, _key: str):
        return self.workbook


def test_google_sheets_api_read_write_ranges() -> None:
    workbook = FakeWorkbook()
    values = FakeValuesService()
    api = GoogleSheetsAPI("sid", FakeGspreadClient(workbook), values)

    api.write_cell("report", "B2", 123)
    api.write_rows("data", "A1", [["a", "b"], [1, 2]])

    assert "report" in workbook.tabs
    assert "data" in workbook.tabs
    assert values.updated[0]["range"] == "report!B2"
    assert values.updated[1]["range"] == "data!A1"

    values.get_payloads["data!A1:ZZ"] = {"values": [["h1", "h2"], ["v1", "v2"]]}
    values.get_payloads["data!A1:Z1"] = {"values": [["h1", "h2"]]}

    assert api.read_rows("data", "A1") == [["h1", "h2"], ["v1", "v2"]]
    assert api.read_header("data", "A:Z", 1) == ["h1", "h2"]


def test_from_colab_initializes_google_clients(monkeypatch) -> None:
    fake_creds = object()
    fake_values = FakeValuesService()

    class FakeBuildService:
        def spreadsheets(self):
            return self

        def values(self):
            return fake_values

    class FakeAuth:
        called = False

        @staticmethod
        def authenticate_user():
            FakeAuth.called = True

    def fake_default(*, scopes):
        assert scopes == ["https://www.googleapis.com/auth/spreadsheets"]
        return fake_creds, "proj"

    fake_workbook = FakeWorkbook()

    def fake_authorize(creds):
        assert creds is fake_creds
        return FakeGspreadClient(fake_workbook)

    def fake_build(name, version, credentials):
        assert (name, version) == ("sheets", "v4")
        assert credentials is fake_creds
        return FakeBuildService()

    import sys

    monkeypatch.setitem(sys.modules, "google.colab", SimpleNamespace(auth=FakeAuth))
    monkeypatch.setitem(sys.modules, "google.colab.auth", FakeAuth)
    monkeypatch.setitem(sys.modules, "google.auth", SimpleNamespace(default=fake_default))
    monkeypatch.setitem(sys.modules, "gspread", SimpleNamespace(authorize=fake_authorize))
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", SimpleNamespace(build=fake_build))

    book = SheetBook.from_colab("spreadsheet-id")

    assert FakeAuth.called is True
    assert book.creds is fake_creds
    assert isinstance(book.api, GoogleSheetsAPI)
