import pytest

from polars_gsquery import Config


def test_config_rejects_duplicate_key() -> None:
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.load_rows(
            [
                ["key", "type", "value"],
                ["country", "string", "JP"],
                ["country", "string", "US"],
            ]
        )


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


def test_config_uses_key_and_type_columns() -> None:
    cfg = Config(key_col="B", type_col="D", value_col="E")
    cfg.load_rows(
        [
            ["ignored", "key", "ignored", "type", "value"],
            ["x", "min_users", "x", "number", 100],
        ]
    )

    ref = cfg.ref("min_users")
    assert ref.type_name == "number"
    assert ref.a1_ref == "config!E2"


def test_config_rejects_invalid_column_label() -> None:
    cfg = Config(key_col="1")
    with pytest.raises(ValueError, match="Invalid column label"):
        cfg.load_rows([["key", "type", "value"]])


def test_config_skips_empty_and_incomplete_rows() -> None:
    cfg = Config()
    cfg.load_rows(
        [
            ["key", "type", "value"],
            ["", "string", "ignored"],
            ["missing_type_only_key"],
            ["country", "string", "JP"],
        ]
    )

    assert cfg.ref("country").a1_ref == "config!C4"


def test_config_header_row_offset_is_reflected_in_a1_ref() -> None:
    cfg = Config(header_row=3)
    cfg.load_rows(
        [
            ["k", "t", "v"],
            ["country", "string", "JP"],
        ]
    )

    assert cfg.ref("country").a1_ref == "config!C4"


def test_config_multi_letter_value_col_is_supported() -> None:
    cfg = Config(value_col="AA")
    cfg.load_rows([["key", "type", "value"], ["min_users", "number", 10]])
    assert cfg.ref("min_users").a1_ref == "config!AA2"


def test_config_type_name_is_case_sensitive() -> None:
    cfg = Config()
    with pytest.raises(ValueError, match="Unsupported config type"):
        cfg.load_rows([["key", "type", "value"], ["country", "STRING", "JP"]])


def test_config_trims_key_and_type_names() -> None:
    cfg = Config()
    cfg.load_rows([["key", "type", "value"], [" country ", " string ", "JP"]])

    assert cfg.ref("country").type_name == "string"
