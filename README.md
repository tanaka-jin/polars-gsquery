# polars-gsquery

Google スプレッドシートの `=QUERY(...)` を、Polars ライクな DSL で安全に組み立てるライブラリです。

- **Python 側は列名ベース**で記述（`Col1`, `Col2` の直書きを避ける）
- ヘッダ行から列名を解決し、内部で `ColN` に変換
- `Config` シート参照で動的条件を構築
- Colab 向けの `SheetBook.from_colab(...)` を提供

---

## できること

### DSL で QUERY を組み立てる

- `select`
- `where`
- `group_by`
- `sort`
- `limit`
- 集計: `sum`, `count`, `avg`, `min`, `max`
- エイリアス: `q.sum("sales").alias("sales_sum")`

### 列名解決（header -> ColN）

- スプレッドシートのヘッダを読み取り、`"sales"` のような列名を `Col3` に変換して QUERY を生成します。
- 空ヘッダ・重複ヘッダはエラーになります。

### Config シート参照（動的条件）

- `q.cfg("key")` を使って、`Config` シート上の値を QUERY 条件に埋め込めます。
- 型変換は `string` / `number` / `date` / `boolean` に対応します。
- `Config` 参照セルが空の場合は、その条件は `1=1` に置き換えられます（動的フィルタの ON/OFF 用）。

### ロケール依存の関数区切り文字

- `en_US`, `ja_JP` などは `,`
- `de_DE` など一部ロケールは `;`

### Colab 向けショートカット

- `SheetBook.from_colab(...)` で Google 認証 + Sheets クライアント初期化をまとめて実行できます。

---

## インストール

```bash
pip install polars-gsquery
```

Colab で `SheetBook.from_colab(...)` を使う場合は extras を推奨します。

```bash
pip install "polars-gsquery[colab]"
```

> ライブラリ本体は軽量で、Colab 連携依存は optional dependencies です。

---

## 最小例（Colab）

```python
import polars as pl
from polars_gsquery import SheetBook, q

SPREADSHEET_ID = "your-spreadsheet-id"

# Colab 用ショートカット（Google認証込み）
book = SheetBook.from_colab(spreadsheet_id=SPREADSHEET_ID, locale="ja_JP")

# 1) データを書き込み（ヘッダ + 行）
df = pl.DataFrame(
    {
        "country": ["JP", "US", "JP"],
        "event_date": ["2026-01-01", "2026-01-03", "2026-01-05"],
        "sales": [100, 120, 180],
    }
)
book.write_mart(df, sheet="data")

# 2) QUERY 式をDSLで構築して report シートに書く
expr = (
    q.from_sheet(data_sheet="data", config_sheet="config", header_rows=1)
    .select(["country", q.sum("sales").alias("sales_sum")])
    .where(q.col("country") == q.cfg("country"))
    .where(q.col("event_date") >= q.cfg("start_date", type_name="date"))
    .group_by("country")
    .sort("sales_sum", descending=True)
    .limit(50)
)

formula = book.write_report(sheet="report_sales", query_expr=expr, anchor_cell="A1")
print(formula)
```

---

## `config` シート形式

デフォルトでは以下の列構成を想定します。

- `A`: `key`
- `B`: `type`
- `C`: `value`

例:

| key        | type    | value      |
|------------|---------|------------|
| country    | string  | JP         |
| start_date | date    | 2026-01-01 |
| min_sales  | number  | 100        |
| enabled    | boolean | TRUE       |

### 挙動

- `key` 重複: エラー
- 未知の `type`: エラー
- `value` が空文字: その条件は `1=1` としてスキップ

### カスタマイズ

列位置を変更したい場合は `Config` を明示します。

```python
from polars_gsquery import Config

cfg = Config(
    sheet="settings",
    header_row=2,
    key_col="B",
    type_col="C",
    value_col="D",
)

book.load_config(cfg)
```

---

## 列指定ポリシー（重要）

Python DSL では **列名（ヘッダ名）または alias** を使ってください。

### OK

```python
q.from_sheet("data").select(["country", q.sum("sales").alias("sales_sum")]).sort("sales_sum")
```

### NG（Python API では非サポート）

```python
q.from_sheet("data").select(["Col2"])
q.from_sheet("data").sort("Col2")
```

`ColN` を使いたいケースは、`q.raw(...)` を使って **生の QUERY 文字列** を明示的に書いてください。

```python
q.from_sheet("data").where("Col2 > 100")
```

---

## DSL の使い方

### 基本の集計

```python
expr = (
    q.from_sheet("data")
    .select([
        "country",
        q.sum("sales").alias("sales_sum"),
        q.avg("sales").alias("sales_avg"),
        q.min("sales").alias("sales_min"),
        q.max("sales").alias("sales_max"),
        q.count("user_id").alias("users"),
    ])
    .group_by("country")
    .sort("sales_sum", descending=True)
    .limit(100)
)
```

### where 条件（複数指定は AND）

```python
expr = q.from_sheet("data").where(
    q.col("country") == "JP",
    q.col("sales") >= 100,
)
```

### `&` / `|` によるブール式

```python
expr = q.from_sheet("data").where(
    ((q.col("a") == 1) | (q.col("b") == 2)) & (q.col("c") == 3)
)
```

### `q.raw(...)`（escape hatch）

`q.raw(...)` では、`q.col(...)` をプレースホルダとして埋め込めます。

```python
# where で raw
expr = q.from_sheet("data").where(
    q.raw(
        "{sales_col} > 100 and {country_col} = 'JP'",
        sales_col=q.col("sales"),
        country_col=q.col("country"),
    )
)

# select で raw
expr = q.from_sheet("data").select([
    q.raw("{left} - {right}", left=q.col("price"), right=q.col("discount"))
])
```

> `q.raw()` のプレースホルダには `q.col(...)` だけを渡せます。

---

## Config 参照の書き方（2通り）

### 1) 手軽な書き方: `q.cfg(...)`

`write_report()` 時に `config_sheet` を見て自動で解決されます。

```python
expr = (
    q.from_sheet(data_sheet="data", config_sheet="config")
    .where(q.col("country") == q.cfg("country"))
    .where(q.col("event_date") >= q.cfg("start_date", type_name="date"))
)
```

### 2) 明示的な書き方: `Config` + `cfg.ref(...)`

型や参照を明示したい場合はこちら。

```python
from polars_gsquery import Config

cfg = book.load_config(Config(sheet="config"))

expr = (
    q.from_sheet(data_sheet="data", config_sheet="config")
    .where(q.col("country") == cfg.ref("country"))
    .where(q.col("event_date") >= cfg.ref("start_date"))
)
```

---

## API 概要（公開 API）

```python
from polars_gsquery import SheetBook, Config, ConfigRef, q
```

### `SheetBook`

- `SheetBook(spreadsheet_id, creds=None, locale="en_US", config_sheet="config", api=None)`
- `SheetBook.from_colab(spreadsheet_id, locale="ja_JP")`
- `load_config(cfg=None, start_cell="A1") -> Config`
- `ensure_config_loaded(expr, start_cell="A1") -> QueryExpr`
- `write_mart(df, sheet="data", start_cell="A1") -> None`
- `get_header_map(sheet, header_row, range_) -> dict[str, str]`
- `write_report(sheet, query_expr, anchor_cell="A1") -> str`

### `q`（DSL namespace）

- `q.from_sheet(data_sheet, config_sheet=None, header_rows=1, range_=None)`
- `q.col(name)`
- `q.sum(...)`, `q.count(...)`, `q.avg(...)`, `q.min(...)`, `q.max(...)`
- `q.cfg(key, type_name="string")`
- `q.raw(query, **columns)`

---

## 仕様メモ / 制約

- `select(...)` を省略（または空）すると `select *`
- `where(cond1, cond2, ...)` は暗黙 AND
- `sort("col")` は昇順、`sort("col", descending=True)` で降順
- 複数キーソート: `sort(["country", "sales_sum"], descending=[False, True])`
- クエリ句の出力順は呼び出し順ではなく、`select -> where -> group by -> order by -> limit -> label`
- QUERY 文字列内の文字列リテラル・label は適切にエスケープ
- シート名に空白や `'` が含まれる場合も適切にクォート

### `range_` 省略時の挙動

- `range_` を省略すると、ヘッダから `A:<最終列>` を推定して QUERY 範囲を作ります。
- 列数が多い場合や範囲を明示したい場合は `range_="A:Z"` のように指定を推奨します。

---

## `write_mart()` で受け取れるオブジェクト

`write_mart()` は Polars DataFrame を想定していますが、以下を満たすオブジェクトなら利用できます。

- `.columns` を持つ
- `.iter_rows()` を持つ

つまり Polars ライクな DataFrame 互換オブジェクトでも使えます。

---

## 開発

```bash
python -m pip install -e ".[dev]"
pytest
```
