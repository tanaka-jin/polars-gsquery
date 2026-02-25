import pytest

from polars_gsquery import Config, q
from polars_gsquery.config_binding import bind_config_refs, has_deferred_config_refs
from polars_gsquery.frame_rows import rows_from_frame, validate_rectangular_rows
from polars_gsquery.header_schema import infer_header_schema
from polars_gsquery.sheets.api import SheetsAPI


class DummyDF:
    columns = ["a", "b"]

    def iter_rows(self):
        yield (1, 2)


def test_config_binding_resolves_deferred_refs() -> None:
    expr = q.from_sheet(data_sheet="data", config_sheet="params").where(q.col("country") == q.cfg("country"))

    assert has_deferred_config_refs(expr)

    cfg = Config(sheet="params")
    cfg.load_rows([["key", "type", "value"], ["country", "string", "JP"]])
    bound = bind_config_refs(expr, cfg)

    assert not has_deferred_config_refs(bound)
    assert bound.predicates[0].right.a1_ref == "params!C2"


def test_infer_header_schema_infers_default_range_from_headers() -> None:
    api = SheetsAPI()
    api.set_header_fixture("data", "A:Z", 1, ["country", "sales"])

    schema = infer_header_schema(api, sheet="data", header_row=1, range_=None)

    assert schema.range_ == "A:B"
    assert schema.header_map == {"country": "Col1", "sales": "Col2"}


def test_rows_from_frame_and_rectangular_validation() -> None:
    rows = rows_from_frame(DummyDF())
    validate_rectangular_rows(rows)
    assert rows == [["a", "b"], [1, 2]]


def test_validate_rectangular_rows_rejects_ragged_rows() -> None:
    with pytest.raises(ValueError, match="ragged rows"):
        validate_rectangular_rows([["a", "b"], [1]])
