import pytest

from polars_sheets_query import Config


def test_config_rejects_duplicate_key() -> None:
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.ensure_params([("country", "string", "JP"), ("country", "string", "US")])


def test_config_ref_returns_a1() -> None:
    cfg = Config(sheet="config", value_col="C")
    cfg.ensure_params([("min_users", "number", 100)])
    ref = cfg.ref("min_users")
    assert ref.a1_ref == "config!C2"
    assert ref.type_name == "number"
