import pytest

from polars_gsquery import Config


def test_config_rejects_duplicate_key() -> None:
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.load_rows([
            ["key", "type", "value"],
            ["country", "string", "JP"],
            ["country", "string", "US"],
        ])


def test_config_ref_returns_a1() -> None:
    cfg = Config(sheet="config", value_col="C")
    cfg.load_rows([["key", "type", "value"], ["min_users", "number", 100]])
    ref = cfg.ref("min_users")
    assert ref.a1_ref == "config!C2"
    assert ref.type_name == "number"


def test_config_ref_quotes_sheet_name_for_a1() -> None:
    cfg = Config(sheet="Bob's sheet", value_col="C")
    cfg.load_rows([["key", "type", "value"], ["country", "string", "O'Reilly"]])
    ref = cfg.ref("country")
    assert ref.a1_ref == "'Bob''s sheet'!C2"
