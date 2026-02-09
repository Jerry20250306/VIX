# VIX Step 0 輸出格式規格文件

## 文件目的
本文件定義 VIX Step 0 計算結果的輸出格式，目標是將我們的輸出格式調整為與 PROD 一致，以便於後續比對與整合。

**重要原則：只調整輸出格式，不更動任何計算邏輯。**

---

## 1. 格式變更概述

### 1.1 主要變更

| 項目 | 目前格式 | 目標格式（PROD 格式） |
|:--|:--|:--|
| **資料結構** | 一列 = (Time, Strike, CP) | 一列 = (time, strike)，Call/Put 用欄位前綴區分 |
| **欄位前綴** | 無前綴，用 `CP` 欄位區分 | `c.` = Call，`p.` = Put |
| **Outlier 標記** | Boolean (True/False) | 字串 ("-"/"1"/"V" 等) |
| **欄位名稱** | 駝峰式 (Q_hat_Bid) | 點分式 (c.bid) |

### 1.2 不變更項目

以下項目維持不變，**絕對不更動**：
- EMA 計算公式與邏輯
- Gamma 參數判定邏輯
- 異常值判定邏輯（Condition 1~4）
- Q_hat 報價選擇邏輯（優先順序：Q_Last → Q_Min → Replacement）
- 所有數值計算邏輯

---

## 2. 目前輸出格式（我們的格式）

### 2.1 檔案結構
- 一列 = 一個 (Time, Strike, CP) 組合
- Call 和 Put 分開為兩列

### 2.2 目前欄位列表

| 欄位名稱 | 類型 | 說明 | 來源程式 |
|:--|:--|:--|:--|
| `Term` | str | "Near" 或 "Next" | step0_valid_quotes.py |
| `Time` | int | 時間（如 84530） | step0_valid_quotes.py |
| `Snapshot_SysID` | int | 快照系統序號 | step0_valid_quotes.py |
| `Strike` | int | 履約價 | step0_valid_quotes.py |
| `CP` | str | "Call" 或 "Put" | step0_valid_quotes.py |
| `Q_last_Bid` | float | Q_Last 原始買價 | step0_valid_quotes.py |
| `Q_last_Ask` | float | Q_Last 原始賣價 | step0_valid_quotes.py |
| `Q_last_SysID` | int | Q_Last 的系統序號 | step0_valid_quotes.py |
| `Q_Last_Valid_Bid` | float/str | 有效報價買價（無效為 "null"）| step0_valid_quotes.py |
| `Q_Last_Valid_Ask` | float/str | 有效報價賣價 | step0_valid_quotes.py |
| `Q_Last_Valid_Spread` | float/str | 價差 | step0_valid_quotes.py |
| `Q_Last_Valid_Mid` | float/str | 中價 | step0_valid_quotes.py |
| `Q_min_Bid` | float | Q_Min 原始買價 | step0_valid_quotes.py |
| `Q_min_Ask` | float | Q_Min 原始賣價 | step0_valid_quotes.py |
| `Q_Min_Valid_Bid` | float/str | 有效報價買價 | step0_valid_quotes.py |
| `Q_Min_Valid_Ask` | float/str | 有效報價賣價 | step0_valid_quotes.py |
| `Q_Min_Valid_Spread` | float/str | 價差 | step0_valid_quotes.py |
| `Q_Min_Valid_Mid` | float/str | 中價 | step0_valid_quotes.py |
| `EMA` | float | 指數移動平均值 | step0_2_ema_calculation.py |
| `EMA_Process` | str | EMA 計算過程（除錯用）| step0_2_ema_calculation.py |
| `Q_Last_Valid_Gamma` | float | Q_Last 的 Gamma 參數 | step0_2_ema_calculation.py |
| `Q_Last_Valid_Is_Outlier` | bool | Q_Last 是否為異常值 | step0_2_ema_calculation.py |
| `Q_Min_Valid_Gamma` | float | Q_Min 的 Gamma 參數 | step0_2_ema_calculation.py |
| `Q_Min_Valid_Is_Outlier` | bool | Q_Min 是否為異常值 | step0_2_ema_calculation.py |
| `Q_hat_Bid` | float | 最終報價買價 | step0_2_ema_calculation.py |
| `Q_hat_Ask` | float | 最終報價賣價 | step0_2_ema_calculation.py |
| `Q_hat_Mid` | float | 最終報價中價 | step0_2_ema_calculation.py |
| `Q_hat_Source` | str | 報價來源（Q_Last/Q_Min/Replacement）| step0_2_ema_calculation.py |

---

## 3. 目標輸出格式（PROD 格式）

### 3.1 檔案結構
- 一列 = 一個 (time, strike) 組合
- Call 和 Put 合併在同一列，用欄位前綴 `c.`/`p.` 區分

### 3.2 目標欄位列表

| 欄位名稱 | 類型 | 說明 | 對應來源 |
|:--|:--|:--|:--|
| `time` | int | 時間（如 84530） | Time |
| `strike` | int | 履約價 | Strike |
| `snapshot_sysID` | int | 快照系統序號 | Snapshot_SysID |
| **Call 欄位** | | | |
| `c.ema` | float | Call 的 EMA | EMA (CP='Call') |
| `c.gamma` | float | Call 的 Gamma（Q_Last）| Q_Last_Valid_Gamma (CP='Call') |
| `c.last_bid` | float | Call 的 Q_Last 買價 | Q_Last_Valid_Bid (CP='Call') |
| `c.last_ask` | float | Call 的 Q_Last 賣價 | Q_Last_Valid_Ask (CP='Call') |
| `c.last_sysID` | int | Call 的 Q_Last 系統序號 | Q_last_SysID (CP='Call') |
| `c.last_outlier` | str | Call 的 Q_Last 異常值標記 | 轉換自 Q_Last_Valid_Is_Outlier |
| `c.min_bid` | float | Call 的 Q_Min 買價 | Q_Min_Valid_Bid (CP='Call') |
| `c.min_ask` | float | Call 的 Q_Min 賣價 | Q_Min_Valid_Ask (CP='Call') |
| `c.min_sysID` | int | Call 的 Q_Min 系統序號 | **需新增** |
| `c.min_outlier` | str | Call 的 Q_Min 異常值標記 | 轉換自 Q_Min_Valid_Is_Outlier |
| `c.bid` | float | Call 的最終報價買價 | Q_hat_Bid (CP='Call') |
| `c.ask` | float | Call 的最終報價賣價 | Q_hat_Ask (CP='Call') |
| `c.source` | str | Call 的報價來源 | Q_hat_Source (CP='Call') |
| **Put 欄位** | | | |
| `p.ema` | float | Put 的 EMA | EMA (CP='Put') |
| `p.gamma` | float | Put 的 Gamma（Q_Last）| Q_Last_Valid_Gamma (CP='Put') |
| `p.last_bid` | float | Put 的 Q_Last 買價 | Q_Last_Valid_Bid (CP='Put') |
| `p.last_ask` | float | Put 的 Q_Last 賣價 | Q_Last_Valid_Ask (CP='Put') |
| `p.last_sysID` | int | Put 的 Q_Last 系統序號 | Q_last_SysID (CP='Put') |
| `p.last_outlier` | str | Put 的 Q_Last 異常值標記 | 轉換自 Q_Last_Valid_Is_Outlier |
| `p.min_bid` | float | Put 的 Q_Min 買價 | Q_Min_Valid_Bid (CP='Put') |
| `p.min_ask` | float | Put 的 Q_Min 賣價 | Q_Min_Valid_Ask (CP='Put') |
| `p.min_sysID` | int | Put 的 Q_Min 系統序號 | **需新增** |
| `p.min_outlier` | str | Put 的 Q_Min 異常值標記 | 轉換自 Q_Min_Valid_Is_Outlier |
| `p.bid` | float | Put 的最終報價買價 | Q_hat_Bid (CP='Put') |
| `p.ask` | float | Put 的最終報價賣價 | Q_hat_Ask (CP='Put') |
| `p.source` | str | Put 的報價來源 | Q_hat_Source (CP='Put') |

---

## 4. 欄位轉換規則

### 4.1 Outlier 標記轉換

**目前格式** → **目標格式**：

```
Q_Last_Valid_Is_Outlier / Q_Min_Valid_Is_Outlier (bool)
    ↓ 轉換
c.last_outlier / c.min_outlier / p.last_outlier / p.min_outlier (str)
```

轉換邏輯：

| 我們的值 | 目標值 | 說明 |
|:--|:--|:--|
| `None` 或無資料 | `"-"` | 無法判定（無雙邊報價）|
| `False` (非異常值) | `"1"` 或 `"2"` 或 `"1,2"` 等 | 符合的條件編號 |
| `True` (異常值) | `"V"` | Violation，異常值 |

**條件編號對照**：
- Condition 1：`Spread <= γ × EMA_t`
- Condition 2：`Mid 在 [Q_hat_Mid_t-1 - γ×EMA_t, Q_hat_Mid_t-1 + γ×EMA_t] 內`
- Condition 3：`Bid 在 [Q_hat_Bid_t-1 - γ×EMA_t, Q_hat_Bid_t-1 + γ×EMA_t] 內`
- Condition 4：`Ask 在 [Q_hat_Ask_t-1 - γ×EMA_t, Q_hat_Ask_t-1 + γ×EMA_t] 內`

### 4.2 資料結構轉換

**Call+Put 合併邏輯**：

```python
# 目前：兩列
# Time=84530, Strike=28900, CP='Call', EMA=123.45, ...
# Time=84530, Strike=28900, CP='Put',  EMA=99.99, ...

# 目標：一列
# time=84530, strike=28900, c.ema=123.45, p.ema=99.99, ...
```

轉換方式（不動計算邏輯，只在最後輸出時處理）：

```python
# 1. 先保持原計算流程不變
# 2. 在輸出 CSV 前，將 Call 和 Put 資料 merge

call_df = result_df[result_df['CP'] == 'Call']
put_df = result_df[result_df['CP'] == 'Put']

# 重命名欄位
call_renamed = call_df.rename(columns={'EMA': 'c.ema', 'Q_hat_Bid': 'c.bid', ...})
put_renamed = put_df.rename(columns={'EMA': 'p.ema', 'Q_hat_Bid': 'p.bid', ...})

# 合併
output_df = pd.merge(call_renamed, put_renamed, on=['time', 'strike', 'snapshot_sysID'])
```

### 4.3 移除欄位

輸出時不包含以下欄位：
- `Term`（因為分開檔案，Near/Next 已經由檔名區分）
- `EMA_Process`（除錯用，正式輸出不需要）
- `CP`（改用欄位前綴）

---

## 5. 需要新增的資料

### 5.1 Q_Min 的 SysID

**問題**：目前 `reconstruct_order_book.py` 沒有輸出 `My_Min_SysID`。

**解決方案**：
在 `SnapshotReconstructor.reconstruct_at()` 的 Q_Min 結果中新增 `My_Min_SysID` 欄位。

**修改位置**：`reconstruct_order_book.py` 第 473-479 行

**目前**：
```python
min_results.append({
    'Strike': strike,
    'CP': cp,
    'My_Min_Bid': min_row['svel_i081_best_buy_price1'],
    'My_Min_Ask': min_row['svel_i081_best_sell_price1'],
    'My_Min_Spread': min_row['Spread']
})
```

**修改後**：
```python
min_results.append({
    'Strike': strike,
    'CP': cp,
    'My_Min_Bid': min_row['svel_i081_best_buy_price1'],
    'My_Min_Ask': min_row['svel_i081_best_sell_price1'],
    'My_Min_Spread': min_row['Spread'],
    'My_Min_SysID': min_row['svel_i081_seqno']  # 新增
})
```

**注意**：這只是新增一個輸出欄位，不影響任何計算邏輯。

---

## 6. 修改範圍說明

### 6.1 程式修改範圍

| 程式 | 修改類型 | 說明 |
|:--|:--|:--|
| `reconstruct_order_book.py` | 新增輸出欄位 | 新增 `My_Min_SysID` |
| `step0_valid_quotes.py` | 新增輸出欄位 | 傳遞 `Q_min_SysID` |
| `step0_2_ema_calculation.py` | 輸出格式轉換 | 新增輸出轉換函式 |

### 6.2 不修改項目（嚴格禁止）

| 函式/邏輯 | 說明 |
|:--|:--|
| `calculate_ema_for_series()` | EMA 計算邏輯 |
| `determine_gamma()` | Gamma 參數決定邏輯 |
| `check_outlier()` | 異常值判定邏輯 |
| `add_ema_and_outlier_detection()` | 報價選擇邏輯 |
| `SnapshotReconstructor.reconstruct_at()` | Q_Last/Q_Min 選擇邏輯（只新增欄位）|
| `check_valid_quote()` | 有效報價檢查邏輯 |

---

## 7. 驗證方式

格式轉換後，使用以下方式驗證數值正確性：

1. **數值比對**：轉換後的數值應與轉換前完全一致
2. **筆數比對**：(time, strike) 組合數 = 原本 (Time, Strike, CP='Call') 筆數 = 原本 (Time, Strike, CP='Put') 筆數
3. **PROD 比對**：使用 `verify_full_day.py` 驗證正確率

---

## 8. 更新紀錄

| 日期 | 修改人 | 內容 |
|:--|:--|:--|
| 2026-02-09 | - | 初版建立 |
| 2026-02-09 | - | 實作完成：新增 My_Min_SysID、Q_min_SysID、PROD 格式轉換函式 |
