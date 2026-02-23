# polars-gsquery

Google スプレッドシートの `=QUERY(...)` を、Polars ライクな DSL で安全に組み立てるライブラリです。

## できること

- `q` DSL で `select / where / group by / order by / limit / label(alias)` を構築
- スプレッドシートのヘッダ行から列名→A1 列記号（`A`, `B`, ...）を自動解決
- `Config` シートの値参照（`string / number / date / boolean`）を動的に QUERY に埋め込み
  - `string` は `SUBSTITUTE(..., "'", "''")` でクォートをエスケープ
  - `date` は `TEXT(..., "yyyy-MM-dd")` で `date 'YYYY-MM-DD'` 形式へ変換
  - `boolean` は `IF(..., "TRUE", "FALSE")` へ変換
- 関数区切り文字はロケール依存（例: `ja_JP` / `en_US` は `,`、`de_DE` は `;`）
- Colab 向けに `SheetBook.from_colab(...)` を提供（Google 認証 + Sheets クライアント初期化）

## インストール

```bash
pip install polars-gsquery
```

`SheetBook.from_colab(...)` を使う場合は、`gspread` / `google-api-python-client` / `google-auth` が必要です。
基本的には extras を使って以下でまとめて入れるのを推奨します。

```bash
pip install 'polars-gsquery[colab]'
```

すでにこれら依存を別で導入済みなら、`pip install polars-gsquery` だけでも動作します。

## 最小例（Colab）

```python
import polars as pl
from polars_gsquery import SheetBook, Config, q

SPREADSHEET_ID = "your-spreadsheet-id"

book = SheetBook.from_colab(spreadsheet_id=SPREADSHEET_ID, locale="ja_JP")

# 1) DataFrame を data シートへ書き込み
#    columns と iter_rows() を持つオブジェクトなら利用できます
#    （polars.DataFrame はそのまま利用可）
df = pl.DataFrame(
    {
        "country": ["JP", "US", "JP"],
        "event_date": ["2026-01-01", "2026-01-03", "2026-01-05"],
        "sales": [100, 120, 180],
    }
)
book.write_mart(df, sheet="data")

# 2) QUERY 式を組み立てて report シートへ配置
#    config_sheet を指定すると write_report 時に自動で config を読み込みます
expr = (
    q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1)
    .select(["country", q.sum("sales").alias("sales_sum")])
    .where(q.col("country") == q.cfg("country"))
    .where(q.col("event_date") >= q.cfg("start_date", type_name="date"))
    .groupby(["country"])
    .orderby([q.desc("sales_sum")])
    .limit(50)
)

formula = book.write_report(sheet="report_sales", query_expr=expr, anchor_cell="A1")
print(formula)
```

## `config` シート形式

- ヘッダ行: `key | type | value`
- `type`: `string | number | date | boolean`
- 例:
  - `country | string | JP`
  - `start_date | date | 2026-01-01`

`Config` は重複 key、未知の type をエラーにします。

## API 概要

- `SheetBook.write_mart(df, sheet="data")`
  - ヘッダ + データを書き込み
  - 行の列数が不一致（ragged rows）の場合は書き込み前にエラー
  - `iter_rows()` が generator でも利用可能
- `SheetBook.load_config(cfg=None)`
  - `Config` にスプレッドシート上の設定値マップをロード
  - `cfg` を省略した場合は、`SheetBook(config_sheet=...)` で指定したシート名を使用
- `SheetBook.write_report(sheet, query_expr, anchor_cell="A1")`
  - ヘッダ検証（空/重複の列名を拒否）
  - `=QUERY(...)` 文字列を生成して指定セルに書き込み

## 制約

- 現在の集計関数は `sum`, `count` のみ
- 条件は `and` 連結のみ（`or` は未対応）
- `where` は `q.col("...") <op> 値` に加えて、生文字列（例: `"B > 100"`）も指定可能
- 生文字列で列参照だけ `q.col` を使いたい場合は `q.raw("{sales} > 100", sales=q.col("sales"))` のようにプレースホルダ置換が可能
- `select(...)` でも `q.raw("{a} - {b}", a=q.col("A"), b=q.col("B"))` のような式列を指定可能（escape hatch）
- 集計引数も Polars ライクに `q.sum("sales")` / `q.sum(q.col("sales"))` を利用可能
- `select(...)` を省略、または空で指定した場合は `select *` として扱います
- `from_sheet(..., range_=...)` の `range_` を省略した場合、ヘッダ列数から `A:<最終列>` を自動推定します

## 開発

```bash
python -m pip install -e . pytest
pytest
```
