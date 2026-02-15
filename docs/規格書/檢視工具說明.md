# VIX 驗證結果瀏覽器 — 開發任務書

> **版本**: v1.0  
> **建立日期**: 2026-02-12  
> **目標讀者**: 初級工程師（具備 Python + HTML/JS 基礎）

---

## 1. 專案概述

### 1.1 目標

開發一個 **本地端 HTML 網頁介面**，用來瀏覽 VIX 計算驗證結果。  
使用者可以：

1. **選擇日期** → 顯示當天的差異報告（`validation_diff_YYYYMMDD.csv`）
2. **點選差異列** → 帶出該筆資料的詳細行情資料（原始 Tick Data）
3. **查看前後兩個時間區間** 的所有行情紀錄，用於追蹤差異原因

### 1.2 架構選型

| 元件 | 技術 |
|------|------|
| **後端** | Python + Flask（輕量 HTTP Server） |
| **前端** | 純 HTML/CSS/JavaScript（無框架） |

```markdown
```markdown
| **資料路徑** | 支援 UI 介面選取，並自動持久化至 `.env` 環境變數（此路徑為最上層目錄，例如本案例的 `output` 目錄） |
```

```

> **為什麼用 Flask？**  
> 因為原始 tick 檔案單檔超過 100MB，前端無法直接讀取。  
> 需要後端 API 做篩選後回傳 JSON。

---

## 2. 資料來源說明

### 2.1 驗證差異報告

**路徑**: `output/validation_diff_YYYYMMDD.csv`  
**格式**: CSV (UTF-8 with BOM)  
**產生方式**: 由 `validation/verify_full_day.py {YYYYMMDD}` 產生

| 欄位 | 型別 | 說明 | 範例 |
|------|------|------|------|
| `Date` | int | 資料日期 (YYYYMMDD) | `20251201` |
| `Time` | int | 時間點 (HMMSS 或 HHMMSS) | `84515`, `91000` |
| `Term` | str | Near / Next | `Near` |
| `Strike` | int | 履約價 | `22000` |
| `CP` | str | Call / Put | `Call` |
| `Column` | str | 差異欄位名稱 | `EMA`, `Gamma` |
| `Ours` | float/str | 我們的計算值 | `150.5` |
| `PROD` | float/str | PROD 的值 | `150.3` |
| `SysID` | int | 當前時間區間的 Snapshot SysID | `31018` |
| `Prev_SysID` | int | 前一個時間區間的 SysID | `30952` |

### 2.2 我們的計算結果

**路徑**: `output/驗證{YYYYMMDD}_{Term}PROD.csv`  
**格式**: CSV (UTF-8 with BOM)  
**範例檔名**: `驗證20251201_NearPROD.csv`

| 主要欄位 | 說明 |
|----------|------|
| `date` | 日期 |
| `time` | 時間 (HHMMSS 格式) |
| `strike` | 履約價 |
| `c.bid`, `c.ask` | Call 的 Q_hat Bid/Ask |
| `p.bid`, `p.ask` | Put 的 Q_hat Bid/Ask |
| `c.ema`, `p.ema` | Call/Put 的 EMA |
| `c.gamma`, `p.gamma` | Call/Put 的 Gamma |
| `c.last_bid`, `c.last_ask` | Call 的 Last Valid Bid/Ask |
| `p.last_bid`, `p.last_ask` | Put 的 Last Valid Bid/Ask |
| `c.min_bid`, `c.min_ask` | Call 的 Min Spread Bid/Ask |
| `p.min_bid`, `p.min_ask` | Put 的 Min Spread Bid/Ask |
| `c.source`, `p.source` | Q_hat 來源 (Q_Last_Valid / Q_Min_Valid / Replacement) |
| `snapshot_sysID` | Snapshot 系統序號 |

### 2.3 PROD 資料

**路徑**: `資料來源/{YYYYMMDD}/{Term}PROD_{YYYYMMDD}.tsv`  
**格式**: TSV (Tab-separated)  
**範例檔名**: `NearPROD_20251201.tsv`  

欄位與上方類似，但多了以下欄位：`c.type`, `p.type`, `c.time`, `p.time`, `alpha`, `lambda`, `snapshot_call_bid`, `snapshot_call_ask`, `snapshot_put_bid`, `snapshot_put_ask` 等。

### 2.4 原始行情 Tick Data（最關鍵的資料源）

**路徑**: `資料來源/J002-11300041_{YYYYMMDD}/temp/*.csv`  
**格式**: TSV (Tab-separated，但副檔名為 .csv)

**命名規則**: `J002-11300041_{YYYYMMDD}_TXO{期別代碼}.csv`

例如 `20251201`:

```

J002-11300041_20251201_TXOX5.csv   ← 2025年12月到期 (Near)
J002-11300041_20251201_TXOA6.csv   ← 2026年 1月到期 (Next)
J002-11300041_20251201_TXOL5.csv   ← 其他月份
J002-11300041_20251201_TXOM6.csv   ← 其他月份

```

**欄位定義** (6 欄):

| 欄位 | 說明 | 範例 |
|------|------|------|
| `svel_i081_yymmdd` | 日期 | `20251201` |
| `svel_i081_prod_id` | 商品代碼 (含履約價+到期月) | `TXO13800X5` |
| `svel_i081_time` | 時間戳 (HHMMSSNNNNNN，12位) | `083010004000` |
| `svel_i081_best_buy_price1` | 最佳買價 (Bid) | `0.1000` |
| `svel_i081_best_sell_price1` | 最佳賣價 (Ask) | `1.5000` |
| `svel_i081_seqno` | 系統序號 (SysID) | `2831` |

**商品代碼解碼規則**:

```

TXO{Strike}{Month}{Year}
例: TXO22000X5
  ├── TXO     → 臺指選擇權
  ├── 22000   → 履約價 22000
  ├── X       → 月份代碼 (A=1月, B=2月, ..., L=12月 for Call)
  │              (M=1月, N=2月, ..., X=12月 for Put)
  └── 5       → 年份末碼 (2025)

```

> **月份對照表**:
>
> | 代碼 | Call 月份 | Put 月份 |
> |------|----------|---------|
> | A / M | 1月 | 1月 |
> | B / N | 2月 | 2月 |
> | ... | ... | ... |
> | L / X | 12月 | 12月 |

### 2.5 Near/Next Term 月份判斷（重要）

**不是** 簡單的「當月=Near、下月=Next」！

實際邏輯（參考 `vix_utils.py` Line 218-231）：
1. 讀取所有 Tick CSV 檔案，解析所有商品代碼中的 `YM`（到期年月）
2. 排序所有出現的 `YM`
3. `unique_yms[0]` = Near（最近到期月）
4. `unique_yms[1]` = Next（次近到期月）

**實務推導捷徑**：直接掃描 Tick 目錄內的 CSV 檔名：
- `TXOX5` → X=12月, 5=2025 → YM=202512
- `TXOA6` → A=1月, 6=2026 → YM=202601

排序後：`[202512, 202601]` → Near=202512, Next=202601

> [!WARNING]
> 結算日前後 Near/Next 會切換。例如 12 月中旬結算後，Near 可能變成 1 月而非 12 月。
> 一定要從實際資料動態判斷，不能硬編碼。

### 2.6 時間區間定義

每 15 秒為一個時間點，從 `08:45:15` 到 `13:45:00`，共 **1200** 個時間點。

**時間格式轉換**: Tick Data 的時間 `083010004000` 代表 `08:30:10.004000`。  
但 validation_diff 和 PROD 中的 `Time` 是 `HMMSS` 或 `HHMMSS` (如 `84515` = `08:45:15`)。

**「前一個時間區間」的意義**:  
例如使用者點選 `Time=91000`（09:10:00），需要查看：
- **當前區間**: `seqno` 介於 `Prev_SysID` 到 `SysID` 之間的 Tick
- **前一區間**: `seqno` 介於更早的某個 SysID 到 `Prev_SysID` 之間的 Tick

> [!IMPORTANT]
> `Prev_SysID` 的「再前一個 SysID」在 diff CSV 中沒有存。  
> 需要從 PROD TSV 中讀取 `snapshot_sysID` 欄位，建立完整的  
> `Time → SysID` 對照表來查詢。

---

## 3. File Tree（檔案樹架構）

```

VIX/
├── viewer/                          # ★ 新增：瀏覽器模組
│   ├── app.py                       # Flask 後端主程式
│   ├── data_loader.py               # 資料讀取邏輯（CSV/TSV 解析）
│   ├── tick_parser.py               # Tick Data 解析（商品代碼→Strike/CP/月份）
│   ├── templates/
│   │   └── index.html               # 主要 HTML 頁面
│   └── static/
│       ├── css/
│       │   └── style.css            # 樣式表
│       └── js/
│           ├── main.js              # 主程式邏輯（事件處理、API 串接）
│           ├── table.js             # 表格渲染與排序
│           └── detail.js            # 明細面板（Tick Data 顯示）
│
├── output/                          # 既有：驗證結果
│   ├── validation_diff_YYYYMMDD.csv
│   ├── 驗證YYYYMMDD_NearPROD.csv
│   └── 驗證YYYYMMDD_NextPROD.csv
│
└── 資料來源/                         # 既有：原始資料
    ├── YYYYMMDD/                    # PROD 資料
    │   ├── NearPROD_YYYYMMDD.tsv
    │   └── NextPROD_YYYYMMDD.tsv
    └── J002-11300041_YYYYMMDD/      # 原始 Tick
        └── temp/
            └── *.csv

```

---

## 4. API Schema（後端介面規格）

### 4.1 GET `/api/dates`

**功能**: 取得所有可用的驗證日期列表

**回應**:

```json
{
  "dates": ["20251201", "20251202", "20251203", "..."]
}
```

**實作要點**: 掃描 `output/` 目錄中 `validation_diff_*.csv` 的檔名，提取日期。

---

### 4.2 GET `/api/diff/{date}`

**功能**: 讀取指定日期的差異報告

**參數**:

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `date` | str | ✅ | 日期，格式 YYYYMMDD |

**回應**:

```json
{
  "date": "20251201",
  "total_diffs": 1234,
  "summary": {
    "Near": {
      "EMA": 156,
      "Gamma": 78,
      "Q_hat_Bid": 0,
      "...": "..."
    },
    "Next": {
      "EMA": 200,
      "Gamma": 384
    }
  },
  "rows": [
    {
      "Date": 20251201,
      "Time": 84515,
      "Term": "Near",
      "Strike": 13800,
      "CP": "Call",
      "Column": "EMA",
      "Ours": null,
      "PROD": 0,
      "SysID": 31018,
      "Prev_SysID": null
    }
  ]
}
```

**實作要點**:

- 讀取 `output/validation_diff_{date}.csv`
- `summary` 是前端快速總覽用：依 Term × Column 分組計數
- `rows` 回傳完整差異列表

---

### 4.3 GET `/api/ticks`

**功能**: 查詢指定條件的原始 Tick Data（**最核心的 API**）

**參數** (Query String):

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `date` | str | ✅ | 日期 YYYYMMDD |
| `term` | str | ✅ | `Near` 或 `Next` |
| `strike` | int | ✅ | 履約價 |
| `cp` | str | ✅ | `Call` 或 `Put` |
| `sys_id` | int | ✅ | 當前時間區間的 SysID |
| `prev_sys_id` | int | ❌ | 前一個時間區間的 SysID |

**回應**:

```json
{
  "query": {
    "date": "20251201",
    "term": "Near",
    "strike": 22000,
    "cp": "Call",
    "sys_id": 31018,
    "prev_sys_id": 30952
  },
  "prod_id": "TXO22000X5",
  "current_interval": {
    "sys_id_range": [30952, 31018],
    "ticks": [
      {
        "time": "084510004000",
        "time_display": "08:45:10.004",
        "bid": 150.0,
        "ask": 160.0,
        "seqno": 30960
      }
    ],
    "count": 12
  },
  "prev_interval": {
    "sys_id_range": [30800, 30952],
    "ticks": [ "..." ],
    "count": 8
  }
}
```

**實作要點**:

- 根據 `date` 找到 `資料來源/J002-11300041_{date}/temp/` 目錄
- 根據 `term` 判斷月份代碼（需要知道 Near/Next 對應的到期月份）
- 根據 `strike` + `cp` + 月份代碼組合出 `prod_id`（如 `TXO22000X5`）
- 在對應的 Tick CSV 中篩選 `prod_id` 且 `seqno` 在指定範圍內的資料
- **「前一區間」**：`seqno` 介於 `prev_sys_id` 之前的某個 snapshot SysID 到 `prev_sys_id` 之間

> [!IMPORTANT]
> **效能注意**: Tick CSV 單檔超過 100MB (數百萬列)。  
> **絕對不要一次全部載入**。必須使用 `chunksize` 分批讀取或用 `grep` 預先篩選。  
> 建議用 `pandas.read_csv(chunksize=100000)` 逐批篩選。

---

### 4.4 GET `/api/prod_row`

**功能**: 查詢 PROD 和我們的計算結果中，指定 (date, time, strike) 的完整一列資料

**參數** (Query String):

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `date` | str | ✅ | 日期 |
| `time` | int | ✅ | 時間點 |
| `strike` | int | ✅ | 履約價 |
| `term` | str | ✅ | Near / Next |

**回應**:

```json
{
  "ours": {
    "time": 84515,
    "strike": 22000,
    "c.bid": 150.5,
    "c.ask": 160.0,
    "c.ema": 155.0,
    "c.gamma": 2.0,
    "...": "..."
  },
  "prod": {
    "time": 84515,
    "strike": 22000,
    "c.bid": 150.3,
    "c.ask": 160.0,
    "c.ema": 155.0,
    "c.gamma": 2.0,
    "...": "..."
  },
  "diffs": ["c.bid"]
}
```

---

## 5. 前端介面 Wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│ VIX 驗證結果瀏覽器                                                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  日期選擇: [ 20251201 ▼ ]    差異總數: 1234 筆                        │
│                                                                      │
│  ┌── 摘要 ──────────────────────────────────────────────────────┐    │
│  │ Near Term:  EMA(156) Gamma(78)                               │    │
│  │ Next Term:  EMA(200) Gamma(384) Q_hat_Bid(5) Q_hat_Ask(3)   │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌── 篩選 ──────────────────────────────────────────────────────┐    │
│  │ Term: [All▼]  Column: [All▼]  CP: [All▼]  Strike: [____]    │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌── 差異列表 ──────────────────────────────────────────────────┐    │
│  │ # │ Time   │ Term │ Strike │ CP   │ Column │ Ours  │ PROD  │    │
│  │───┼────────┼──────┼────────┼──────┼────────┼───────┼───────│    │
│  │ 1 │ 084515 │ Near │ 13800  │ Call │ EMA    │ NaN   │ 0     │ ← │
│  │ 2 │ 084515 │ Near │ 15400  │ Call │ EMA    │ NaN   │ 0     │    │
│  │ 3 │ 084515 │ Near │ 16600  │ Call │ EMA    │ NaN   │ 0     │    │
│  │ ...                                                          │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ═══════════════════════════ 點選展開 ═══════════════════════════    │
│                                                                      │
│  ┌── 明細面板（點選後顯示）────────────────────────────────────┐    │
│  │                                                              │    │
│  │ 📌 Date=20251201, Time=84515, Near, Strike=13800, Call       │    │
│  │ SysID=31018, Prev_SysID=30952                                │    │
│  │                                                              │    │
│  │ ── PROD vs Ours 完整比對 ──                                  │    │
│  │ │ 欄位       │ Ours   │ PROD   │ 差異? │                    │    │
│  │ │ c.ema      │ NaN    │ 0      │ ✗    │                    │    │
│  │ │ c.gamma    │ 1.2    │ 1.2    │ ✓    │                    │    │
│  │ │ c.bid      │ 0.0    │ 0.0    │ ✓    │                    │    │
│  │ │ ...        │        │        │       │                    │    │
│  │                                                              │    │
│  │ ── 當前區間 Tick (SysID 30952~31018) ──                      │    │
│  │ │ Time             │ Bid    │ Ask    │ SysID │               │    │
│  │ │ 08:45:10.004     │ 0.1    │ 0.0    │ 30960 │               │    │
│  │ │ 08:45:12.500     │ 0.1    │ 1.5    │ 30998 │               │    │
│  │ │ ...                                                        │    │
│  │                                                              │    │
│  │ ── 前一區間 Tick (SysID ???~30952) ──                         │    │
│  │ │ Time             │ Bid    │ Ask    │ SysID │               │    │
│  │ │ 08:44:55.120     │ 0.0    │ 0.0    │ 30800 │               │    │
│  │ │ ...                                                        │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Pseudo-code（虛擬碼）

### 6.1 後端：`app.py`

```python
# ===== Flask 後端主程式 =====
from flask import Flask, render_template, jsonify, request
from data_loader import DiffLoader, ProdLoader, TickLoader

app = Flask(__name__)

# 初始化資料載入器
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_ROOT)  # VIX/
diff_loader = DiffLoader(os.path.join(BASE_DIR, "output"))
prod_loader = ProdLoader(os.path.join(BASE_DIR, "output"), os.path.join(BASE_DIR, "資料來源"))
tick_loader = TickLoader(os.path.join(BASE_DIR, "資料來源"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/dates")
def get_dates():
    # 掃描 output/ 中的 validation_diff_*.csv
    dates = diff_loader.list_available_dates()
    return jsonify({"dates": dates})

@app.route("/api/diff/<date>")
def get_diff(date):
    df = diff_loader.load(date)
    
    # 產生摘要 (Term × Column 的筆數)
    summary = {}
    for term in df["Term"].unique():
        term_df = df[df["Term"] == term]
        summary[term] = term_df["Column"].value_counts().to_dict()
    
    return jsonify({
        "date": date,
        "total_diffs": len(df),
        "summary": summary,
        "rows": df.to_dict(orient="records")
    })

@app.route("/api/ticks")
def get_ticks():
    date = request.args["date"]
    term = request.args["term"]
    strike = int(request.args["strike"])
    cp = request.args["cp"]
    sys_id = int(request.args["sys_id"])
    prev_sys_id = request.args.get("prev_sys_id")  # 可選
    
    if prev_sys_id and prev_sys_id != 'nan':
        prev_sys_id = int(float(prev_sys_id))
    else:
        prev_sys_id = None
    
    result = tick_loader.query(date, term, strike, cp, sys_id, prev_sys_id)
    return jsonify(result)

@app.route("/api/prod_row")
def get_prod_row():
    date = request.args["date"]
    time_val = int(request.args["time"])
    strike = int(request.args["strike"])
    term = request.args["term"]
    
    ours = prod_loader.get_ours_row(date, term, time_val, strike)
    prod = prod_loader.get_prod_row(date, term, time_val, strike)
    
    # 比對差異欄位
    diffs = []
    for col in ours.keys():
        if col in prod and str(ours[col]) != str(prod[col]):
            diffs.append(col)
    
    return jsonify({"ours": ours, "prod": prod, "diffs": diffs})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

---

### 6.2 後端：`data_loader.py`

```python
# ===== 資料讀取邏輯 =====
import pandas as pd
import os
import glob
import re

class DiffLoader:
    """讀取 validation_diff_*.csv"""
    
    def __init__(self, output_dir):
        self.output_dir = output_dir
    
    def list_available_dates(self):
        """掃描所有可用日期"""
        pattern = os.path.join(self.output_dir, "validation_diff_*.csv")
        files = glob.glob(pattern)
        dates = []
        for f in files:
            # 從檔名提取日期
            match = re.search(r"validation_diff_(\d{8})\.csv", os.path.basename(f))
            if match:
                dates.append(match.group(1))
        return sorted(dates)
    
    def load(self, date):
        """讀取指定日期的差異報告"""
        path = os.path.join(self.output_dir, f"validation_diff_{date}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"找不到差異報告: {path}")
        df = pd.read_csv(path, encoding="utf-8-sig")
        # 處理 NaN → None（JSON 相容）
        df = df.where(pd.notnull(df), None)
        return df


class ProdLoader:
    """讀取我們的計算結果和 PROD 資料"""
    
    def __init__(self, output_dir, source_dir):
        self.output_dir = output_dir
        self.source_dir = source_dir
        self._cache = {}   # 快取已讀取的 DataFrame
    
    def get_ours_row(self, date, term, time_val, strike):
        """取得我們的計算結果中特定 (time, strike) 的一列"""
        key = f"ours_{date}_{term}"
        if key not in self._cache:
            path = os.path.join(self.output_dir, f"驗證{date}_{term}PROD.csv")
            self._cache[key] = pd.read_csv(path, encoding="utf-8-sig")
        
        df = self._cache[key]
        row = df[(df["time"] == time_val) & (df["strike"] == strike)]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()
    
    def get_prod_row(self, date, term, time_val, strike):
        """取得 PROD 中特定 (time, strike) 的一列"""
        key = f"prod_{date}_{term}"
        if key not in self._cache:
            path = os.path.join(self.source_dir, date, f"{term}PROD_{date}.tsv")
            self._cache[key] = pd.read_csv(path, sep="\t")
        
        df = self._cache[key]
        row = df[(df["time"] == time_val) & (df["strike"] == strike)]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()
```

---

### 6.3 後端：`tick_parser.py`（最複雜的部分）

```python
# ===== Tick Data 解析邏輯 =====
import pandas as pd
import os
import glob

# 月份代碼對照表
# Call: A=1, B=2, ..., L=12
# Put:  M=1, N=2, ..., X=12
CALL_MONTH_CODES = {1:'A', 2:'B', 3:'C', 4:'D', 5:'E', 6:'F',
                    7:'G', 8:'H', 9:'I', 10:'J', 11:'K', 12:'L'}
PUT_MONTH_CODES  = {1:'M', 2:'N', 3:'O', 4:'P', 5:'Q', 6:'R',
                    7:'S', 8:'T', 9:'U', 10:'V', 11:'W', 12:'X'}


class TickLoader:
    
    def __init__(self, source_dir):
        self.source_dir = source_dir
    
    def _find_tick_dir(self, date):
        """找到 J002-*_{date}/temp/ 目錄"""
        pattern = os.path.join(self.source_dir, f"J002*{date}", "temp")
        candidates = glob.glob(pattern)
        if not candidates:
            raise FileNotFoundError(f"找不到 Tick 資料: {pattern}")
        return candidates[0]
    
    def _determine_month_and_year(self, date, term):
        """
        根據日期和 Near/Next，決定到期月份和年份
        
        ★ 重要：不能用「當月/下月」簡單判斷！
        
        正確做法：
        1. 讀取 PROD TSV 檔案，取得實際的商品代碼
        2. 從商品代碼中解析出月份代碼
        
        或者更簡單的方法：
        讀取 PROD TSV 的第一筆有效 (非 NaN) 的 strike 資料，
        看它的 c.type / p.type 欄位中的 time 對應到哪個 Tick 檔
        
        最簡易做法（推薦）：
        直接掃描 Tick 目錄內的所有 CSV 檔名，
        解析月份代碼後排序，smallest = Near, second = Next
        """
        tick_dir = self._find_tick_dir(date)
        tick_files = glob.glob(os.path.join(tick_dir, "*.csv"))
        
        # 從檔名提取月份代碼 (e.g., TXOX5 → X,5)
        month_year_pairs = []
        for f in tick_files:
            basename = os.path.basename(f)
            # 檔名格式: J002-..._TXO{月份碼}{年碼}.csv
            # 例: J002-11300041_20251201_TXOX5.csv
            match = re.search(r'TXO([A-X])(\d)\.csv', basename)
            if match:
                code_char = match.group(1)  # X
                year_digit = match.group(2) # 5
                # 解析月份
                all_codes = {**{v: k for k, v in CALL_MONTH_CODES.items()},
                             **{v: k for k, v in PUT_MONTH_CODES.items()}}
                if code_char in all_codes:
                    month = all_codes[code_char]
                    ym = (2020 + int(year_digit)) * 100 + month
                    month_year_pairs.append((ym, code_char, year_digit))
        
        # 去重並排序
        unique_yms = sorted(set(month_year_pairs), key=lambda x: x[0])
        
        if term == "Near":
            target = unique_yms[0] if unique_yms else None
        else:  # Next
            target = unique_yms[1] if len(unique_yms) > 1 else None
        
        if not target:
            raise ValueError(f"無法判斷 {term} 的到期月份")
        
        return target  # (ym, month_code_char, year_digit)
    
    def _build_prod_id(self, strike, cp, month, year_code):
        """組合商品代碼，如 TXO22000X5"""
        if cp == "Call":
            month_code = CALL_MONTH_CODES[month]
        else:
            month_code = PUT_MONTH_CODES[month]
        return f"TXO{strike}{month_code}{year_code}"
    
    def query(self, date, term, strike, cp, sys_id, prev_sys_id=None):
        """
        核心查詢邏輯
        
        1. 找到 Tick CSV 檔案
        2. 判斷到期月份（從檔名動態解析）
        3. 組合 prod_id
        4. 在 CSV 中篩選特定 prod_id + seqno 範圍
        """
        tick_dir = self._find_tick_dir(date)
        
        # ★ 使用動態月份判斷
        ym_info = self._determine_month_and_year(date, term)
        ym, month_code_char, year_digit = ym_info
        month = ym % 100
        
        prod_id = self._build_prod_id(strike, cp, month, year_digit)
        
        # 搜尋檔名符合的 CSV（檔名含 Call 或 Put 的月份碼）
        # 注意：一個 Tick CSV 同時包含 Call 和 Put 資料
        # 所以搜尋時要用「任何」出現在該到期月份的月份碼
        call_code = CALL_MONTH_CODES[month]
        put_code = PUT_MONTH_CODES[month]
        
        tick_file = None
        for code in [call_code, put_code]:
            pattern = os.path.join(tick_dir, f"*TXO{code}{year_digit}.csv")
            tick_files = glob.glob(pattern)
            if tick_files:
                tick_file = tick_files[0]
                break
        
        if not tick_file:
            return {"error": f"找不到 Tick 檔", "prod_id": prod_id}
        
        # 效能關鍵：使用 chunksize 分批讀取
        current_ticks = []
        prev_ticks = []
        
        # ★ 注意：Tick CSV 雖副檔名 .csv，但實際是 Tab-separated
        # ★ 而且第一行 header 可能整行是一個 tab-separated string
        #    被 pandas 當作單欄讀入
        # 正確讀法：sep='\t'
        for chunk in pd.read_csv(tick_file, sep="\t", chunksize=100000):
            # 欄位名稱（6 欄）
            # svel_i081_yymmdd | svel_i081_prod_id | svel_i081_time
            # svel_i081_best_buy_price1 | svel_i081_best_sell_price1 | svel_i081_seqno
            cols = chunk.columns
            id_col = cols[1]   # svel_i081_prod_id
            time_col = cols[2] # svel_i081_time (12位: HHMMSSNNNNNN)
            bid_col = cols[3]  # svel_i081_best_buy_price1
            ask_col = cols[4]  # svel_i081_best_sell_price1
            seq_col = cols[5]  # svel_i081_seqno
            
            # ★★★ 重要：prod_id 欄位有尾隨空白，必須 strip！
            chunk[id_col] = chunk[id_col].astype(str).str.strip()
            
            # 篩選指定商品
            matched = chunk[chunk[id_col] == prod_id]
            
            if matched.empty:
                continue
            
            # 篩選 seqno 範圍
            matched[seq_col] = pd.to_numeric(matched[seq_col], errors="coerce")
            
            # 當前區間: prev_sys_id < seqno <= sys_id
            if prev_sys_id:
                curr = matched[
                    (matched[seq_col] > prev_sys_id) & 
                    (matched[seq_col] <= sys_id)
                ]
            else:
                curr = matched[matched[seq_col] <= sys_id]
            
            for _, row in curr.iterrows():
                current_ticks.append({
                    "time": str(row[time_col]),
                    "time_display": format_tick_time(row[time_col]),
                    "bid": float(row[bid_col]),
                    "ask": float(row[ask_col]),
                    "seqno": int(row[seq_col])
                })
            
            # 前一區間
            # ★ 精確做法：需要查「再前一個 SysID」
            # 方法：建立 Time→SysID 對照表（從 PROD TSV 的 snapshot_sysID 欄位）
            # 簡化做法：取 prev_sys_id 往前 500 筆 seqno 範圍
            if prev_sys_id:
                # 從 PROD TSV 建立 schedule: {time: snapshot_sysID}
                # 然後找 prev_sys_id 對應的時間，再找該時間的前一個時間的 SysID
                # 這裡先用簡化方式
                prev = matched[
                    (matched[seq_col] > (prev_sys_id - 500)) & 
                    (matched[seq_col] <= prev_sys_id)
                ]
                for _, row in prev.iterrows():
                    prev_ticks.append({
                        "time": str(row[time_col]),
                        "time_display": format_tick_time(row[time_col]),
                        "bid": float(row[bid_col]),
                        "ask": float(row[ask_col]),
                        "seqno": int(row[seq_col])
                    })
        
        return {
            "prod_id": prod_id,
            "current_interval": {
                "sys_id_range": [prev_sys_id, sys_id],
                "ticks": sorted(current_ticks, key=lambda x: x["seqno"]),
                "count": len(current_ticks)
            },
            "prev_interval": {
                "ticks": sorted(prev_ticks, key=lambda x: x["seqno"]),
                "count": len(prev_ticks)
            }
        }


def format_tick_time(raw_time):
    """將 Tick 時間 083010004000 轉為 08:30:10.004"""
    s = str(raw_time).strip()
    if len(s) >= 12:
        return f"{s[0:2]}:{s[2:4]}:{s[4:6]}.{s[6:9]}"
    return s
```

---

### 6.4 前端：`main.js`（核心互動邏輯）

```javascript
// ===== 前端主程式 =====

// 1. 頁面載入 → 呼叫 /api/dates → 填入日期下拉選單
async function init() {
    const res = await fetch("/api/dates");
    const data = await res.json();
    
    const select = document.getElementById("date-selector");
    data.dates.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = d;
        select.appendChild(opt);
    });
    
    select.addEventListener("change", onDateChange);
}

// 2. 選擇日期 → 呼叫 /api/diff/{date} → 渲染摘要 + 差異表格
async function onDateChange(e) {
    const date = e.target.value;
    if (!date) return;
    
    showLoading(true);
    const res = await fetch(`/api/diff/${date}`);
    const data = await res.json();
    showLoading(false);
    
    renderSummary(data.summary, data.total_diffs);
    renderDiffTable(data.rows);
}

// 3. 點選差異列 → 呼叫 /api/ticks + /api/prod_row → 顯示明細面板
async function onRowClick(row) {
    const detailPanel = document.getElementById("detail-panel");
    detailPanel.style.display = "block";
    
    // 同時查詢 Tick Data 和 PROD 完整列
    const [tickRes, prodRes] = await Promise.all([
        fetch(`/api/ticks?date=${row.Date}&term=${row.Term}&strike=${row.Strike}&cp=${row.CP}&sys_id=${row.SysID}&prev_sys_id=${row.Prev_SysID}`),
        fetch(`/api/prod_row?date=${row.Date}&time=${row.Time}&strike=${row.Strike}&term=${row.Term}`)
    ]);
    
    const tickData = await tickRes.json();
    const prodData = await prodRes.json();
    
    renderDetailHeader(row);
    renderComparisonTable(prodData);
    renderTickTable("當前區間", tickData.current_interval);
    renderTickTable("前一區間", tickData.prev_interval);
}
```

---

## 7. 開發步驟建議

> 建議按照以下順序開發，每完成一步都可以先測試。

### Phase 1：骨架（約 2 小時）

- [ ] 建立 `viewer/` 資料夾結構
- [ ] 安裝 Flask: `pip install flask`
- [ ] 實作 `app.py` 基本路由 + `GET /api/dates`
- [ ] 實作 `index.html` 空頁面 + 日期下拉選單
- [ ] 驗收：啟動 `python viewer/app.py`，瀏覽器開啟 `localhost:5000` 看到日期選單

### Phase 2：差異報告（約 3 小時）

- [ ] 實作 `DiffLoader.load()`
- [ ] 實作 `GET /api/diff/{date}`
- [ ] 前端：選日期後顯示摘要 + 差異表格
- [ ] 加入篩選功能（Term / Column / CP）
- [ ] 驗收：選 `20251201` 可以看到差異列表

### Phase 3：明細面板（約 4 小時）

- [ ] 實作 `ProdLoader.get_ours_row()` 和 `get_prod_row()`
- [ ] 實作 `GET /api/prod_row`
- [ ] 前端：點選差異列 → 顯示 PROD vs Ours 完整比對表
- [ ] 差異欄位用紅色 highlight
- [ ] 驗收：點選一筆差異，可以看到完整欄位對照

### Phase 4：Tick Data 查詢（約 5 小時，最困難）

- [ ] 實作 `tick_parser.py`：月份代碼解析、prod_id 組合
- [ ] 實作分批讀取 Tick CSV 的邏輯（chunksize）
- [ ] 實作 `GET /api/ticks`
- [ ] 前端：顯示當前區間 + 前一區間的 Tick 資料
- [ ] 驗收：點選差異列後，可以看到原始行情

### Phase 5：Polish（約 2 小時）

- [ ] 表格排序功能
- [ ] 分頁（差異列表可能有上千筆）
- [ ] 載入動畫
- [ ] 錯誤處理與提示

---

## 8. 注意事項與常見陷阱

> [!CAUTION]
> **Tick Data 檔案非常大**（單檔 100MB+），絕對不能一次讀入前端。  
> 必須在後端做篩選，只回傳目標 Strike + SysID 範圍內的資料。

> [!WARNING]
> **月份代碼邏輯可能因換月而與預期不同**。  
> 例如 12 月中旬，Near Term 可能已經是 1 月到期，而非 12 月。  
> 建議從 `vix_utils.py` 的 `determine_near_next_months()` 函式取得正確判斷邏輯。

> [!IMPORTANT]
> **Tick CSV 的分隔符號是 Tab**，但副檔名是 `.csv`，讀取時要用 `sep="\t"`。

> [!NOTE]
> **prod_id 中的空白**：原始資料中 `svel_i081_prod_id` 欄位可能有尾隨空白，  
> 必須先 `.strip()` 再做比對。

> [!TIP]
> **開發時的快捷測試**：可以先用一個小檔案（例如只取 Tick CSV 的前 1000 行）建立測試資料，加速開發迭代。  
> `head -n 1000 原始檔.csv > test_ticks.csv`

---

## 9. 相關文件參考

| 文件 | 路徑 | 用途 |
|------|------|------|
| 驗證腳本 | `validation/verify_full_day.py` | 產生 validation_diff CSV |
| 路徑管理 | `vix_utils.py` | DataPathManager, 月份判斷 |
| EMA 計算 | `step0_2_ema_calculation.py` | 產生 NearPROD/NextPROD CSV |
| 欄位對應表 | `output/欄位對應表.md` | PROD vs Ours 欄位映射 |
