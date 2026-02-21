# polars-gsquery

MVP library to generate Google Sheets `=QUERY(...)` formulas from a small Python DSL.

## Quickstart

```python
from polars_sheets_query import SheetBook, Config, q

book = SheetBook("spreadsheet-id", locale="ja_JP")

cfg = Config(sheet="config")
cfg.ensure_params([
    ("country", "string", "JP"),
    ("start_date", "date", "2026-01-01"),
    ("min_users", "number", 100),
])
book.apply_config(cfg)

expr = (
    q.from_sheet("mart", header_rows=1, range_="A:Z")
    .select(["country", q.sum("sales").alias("sales_sum")])
    .where(q.col("country") == cfg.ref("country"))
    .where(q.col("event_date") >= cfg.ref("start_date"))
    .groupby(["country"])
    .limit(50)
)

formula = book.write_report("report_sales", expr, anchor_cell="A1")
print(formula)
```

## MVP scope

- Config sheet generation (`key/type/value/note`) and typed references.
- Column-name to `ColN` resolution from mart header row.
- DSL: `from_sheet`, `select`, `where`, `groupby`, `sum`, `count`, `orderby`, `limit`.
- Locale-aware argument delimiters: `en_US => ,`, `ja_JP => ;`.

## Constraints

- String config values containing single quote (`'`) are not escaped yet.
- Column order changes in source sheets can break generated formulas.
