# polars-gsquery

Google Spreadsheet の `=QUERY(...)` を、PolarsライクなDSLから組み立てる最小ライブラリです。

## 事前に必要なスプレッドシート

- `config` シート（人が編集する）
  - ヘッダ行: `key | type | value`
  - `type`: `string | number | date | boolean`
  - 例:
    - `country | string | JP`
    - `start_date | date | 2026-01-01`
- `data` シート（単一の mart）
  - Python側で `polars.DataFrame` をそのまま書き込む前提
- `report_sales` シート（空でOK）
  - `A1` に生成された `=QUERY(...)` が配置される

## Colabで動かす最小Example

```python
# pip install polars-gsquery polars
import polars as pl
from polars_gsquery import SheetBook, Config, q

SPREADSHEET_ID = "your-spreadsheet-id"

# Colab前提のコンストラクタ（MVPではAPI注入しやすい形）
book = SheetBook.from_colab(spreadsheet_id=SPREADSHEET_ID, locale="ja_JP")

# 1) 単一DataFrameをdataシートへ書き込み（mart）
df = pl.DataFrame(
    {
        "country": ["JP", "US", "JP"],
        "event_date": ["2026-01-01", "2026-01-03", "2026-01-05"],
        "sales": [100, 120, 180],
    }
)
book.write_mart(df, sheet="data")

# 2) configはスプシ上の既存値を読む（Pythonで初期値を配らない）
cfg = Config(sheet="config")
book.load_config(cfg)

# 3) report用QUERY式を生成・配置
expr = (
    q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1, range_="A:Z")
    .select(["country", q.sum("sales").alias("sales_sum")])
    .where(q.col("country") == cfg.ref("country"))
    .where(q.col("event_date") >= cfg.ref("start_date"))
    .groupby(["country"])
    .limit(50)
)

formula = book.write_report(sheet="report_sales", query_expr=expr, anchor_cell="A1")
print(formula)
```

`config!C2` や `config!C3` を編集すると、`report_sales` の結果はSpreadsheet内で再計算されます（Python再実行不要）。

## 制約（MVP）

- `config` の string 値に `'` が入る場合のエスケープは未対応
- `data` の列順が変わると `ColN` 対応が崩れる可能性がある
