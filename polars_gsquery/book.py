from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .config import Config, ConfigRef
from .qdsl.ast import Predicate, QueryExpr, RawExpr
from .qdsl.compile import compile_formula
from .sheets.api import GoogleSheetsAPI, SheetsAPI, SupportsSheetsAPI


class SupportsDataFrame(Protocol):
    columns: list[str]

    def iter_rows(self) -> Iterable[tuple[object, ...]]: ...


@dataclass
class SheetBook:
    spreadsheet_id: str
    creds: object | None = None
    locale: str = "en_US"
    config_sheet: str = "config"
    api: SupportsSheetsAPI | None = None

    def __post_init__(self) -> None:
        if self.api is None:
            self.api = SheetsAPI()

    @classmethod
    def from_colab(cls, spreadsheet_id: str, locale: str = "ja_JP") -> "SheetBook":
        """Colab-first constructor with Google auth + Sheets clients."""
        import gspread
        from google.auth import default
        from google.colab import auth
        from googleapiclient.discovery import build

        auth.authenticate_user()
        creds, _ = default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gspread_client = gspread.authorize(creds)
        values_service = build("sheets", "v4", credentials=creds).spreadsheets().values()

        api = GoogleSheetsAPI(
            spreadsheet_id=spreadsheet_id,
            gspread_client=gspread_client,
            values_service=values_service,
        )
        return cls(spreadsheet_id=spreadsheet_id, creds=creds, locale=locale, api=api)

    def load_config(self, cfg: Config | None = None, start_cell: str = "A1") -> Config:
        target = cfg if cfg is not None else Config(sheet=self.config_sheet)
        rows = self._require_api().read_rows(target.sheet, start_cell=start_cell)
        target.load_rows(rows)
        return target

    def ensure_config_loaded(self, expr: QueryExpr, start_cell: str = "A1") -> QueryExpr:
        if expr.config_sheet is None or not _has_deferred_config_refs(expr):
            return expr

        cfg = Config(sheet=expr.config_sheet)
        self.load_config(cfg, start_cell=start_cell)
        return _bind_config_refs(expr, cfg)

    def write_mart(self, df: SupportsDataFrame, sheet: str = "data", start_cell: str = "A1") -> None:
        """Write a single polars.DataFrame to Sheet as mart/data source."""
        api = self._require_api()
        rows = _rows_from_frame(df)
        _validate_rectangular_rows(rows)
        api.write_rows(sheet, start_cell, rows)

        if isinstance(api, SheetsAPI):
            api.set_header_fixture(sheet, "A:Z", 1, rows[0])

    def get_header_map(self, sheet: str, header_row: int, range_: str) -> dict[str, str]:
        try:
            headers = self._require_api().read_header(sheet, range_, header_row)
        except KeyError as exc:
            raise ValueError(f"Failed to read header row: {sheet}!{range_} row={header_row}") from exc

        if not headers:
            raise ValueError(f"Header row is empty or missing: {sheet}!{range_} row={header_row}")

        header_map: dict[str, str] = {}
        for i, raw_name in enumerate(headers, start=1):
            name = str(raw_name).strip()
            if not name:
                raise ValueError(
                    f"Header contains an empty column name at {sheet}!{_column_index_to_a1(i)}{header_row}"
                )
            if name in header_map:
                raise ValueError(
                    f"Header contains duplicate column name: {name!r} at {sheet}!{_column_index_to_a1(i)}{header_row}"
                )
            header_map[name] = _column_index_to_a1(i)
        return header_map

    def write_report(self, sheet: str, query_expr: QueryExpr, anchor_cell: str = "A1") -> str:
        api = self._require_api()
        api.ensure_sheet(sheet)

        resolved_expr = self.ensure_config_loaded(query_expr)
        header_range = resolved_expr.range_ if resolved_expr.range_ is not None else "A:Z"
        header_map = self.get_header_map(resolved_expr.data_sheet, resolved_expr.header_rows, header_range)

        if resolved_expr.range_ is None:
            resolved_expr = resolved_expr.with_range(f"A:{_column_index_to_a1(len(header_map))}")

        compiled = compile_formula(resolved_expr, header_map=header_map, locale=self.locale)
        api.write_cell(sheet, anchor_cell, compiled.formula)
        return compiled.formula

    def _require_api(self) -> SupportsSheetsAPI:
        if self.api is None:
            raise RuntimeError("Sheets API is not initialized")
        return self.api


def _rows_from_frame(df: SupportsDataFrame) -> list[list[object]]:
    columns = [str(c) for c in df.columns]
    values = [list(row) for row in df.iter_rows()]
    return [columns, *values]


def _column_index_to_a1(index: int) -> str:
    if index < 1:
        raise ValueError("index must be >= 1")

    out: list[str] = []
    n = index
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out.append(chr(ord("A") + rem))
    return "".join(reversed(out))


def _validate_rectangular_rows(rows: list[list[object]]) -> None:
    if not rows:
        raise ValueError("write_mart produced no rows")

    header_width = len(rows[0])
    for i, row in enumerate(rows, start=1):
        if len(row) != header_width:
            raise ValueError(
                f"write_mart wrote ragged rows: row {i} has {len(row)} columns but header has {header_width}"
            )


def _has_deferred_config_refs(expr: QueryExpr) -> bool:
    for predicate in expr.predicates:
        if isinstance(predicate, Predicate) and _is_deferred_config_ref(predicate.right):
            return True
    return False


def _is_deferred_config_ref(value: object) -> bool:
    return isinstance(value, ConfigRef) and value.a1_ref.startswith("__CONFIG_KEY__:")


def _bind_config_refs(expr: QueryExpr, cfg: Config) -> QueryExpr:
    return QueryExpr(
        data_sheet=expr.data_sheet,
        config_sheet=expr.config_sheet,
        range_=expr.range_,
        header_rows=expr.header_rows,
        selected=expr.selected,
        predicates=tuple(_bind_predicate_config_ref(p, cfg) for p in expr.predicates),
        group_keys=expr.group_keys,
        order=expr.order,
        limit_n=expr.limit_n,
    )


def _bind_predicate_config_ref(predicate: Predicate | RawExpr, cfg: Config) -> Predicate | RawExpr:
    if isinstance(predicate, RawExpr):
        return predicate

    if _is_deferred_config_ref(predicate.right):
        right = predicate.right
        assert isinstance(right, ConfigRef)
        key = right.a1_ref.removeprefix("__CONFIG_KEY__:")
        return Predicate(left=predicate.left, op=predicate.op, right=cfg.ref(key))

    return predicate
