# VIX 計算專案

Taiwan VIX (波動率指數) 計算實作專案

## 專案說明

本專案實作台灣期貨交易所的 VIX (波動率指數) 計算邏輯，包含：

### 已完成功能

- **訂單簿重建** (`reconstruct_order_book.py`): 從原始 tick 資料重建完整的訂單簿快照
- **Step 0-1: 有效報價驗證** (`step0_valid_quotes.py`): 
  - 驗證 Q_last 和 Q_min 報價的有效性
  - 產生詳細報表包含所有驗證結果
- **Step 0-2: EMA 異常值偵測** (`step0_2_ema_calculation.py`):
  - 計算價差的指數移動平均 (EMA, α=0.95)
  - 使用 4 個條件判定異常值
  - 自動判定 γ 參數 (γ₀=1.2, γ₁=2.0, γ₂=2.5)
  - 提供詳細的 EMA 和 Gamma 計算過程說明

### 資料結構

- **原始資料**: Tick-by-tick 交易資料（需放置於 `資料來源/` 目錄）
- **排程資料**: NearPROD 和 NextPROD 快照時間排程
- **輸出報表**: CSV 和 HTML 格式的詳細分析報表

### 主要檔案

- `reconstruct_order_book.py`: 訂單簿重建模組
- `step0_valid_quotes.py`: 步驟一 - 有效報價選擇
- `step0_2_ema_calculation.py`: 步驟二 - EMA 異常值偵測
- `vix_utils.py`: 共用工具函數

### 使用方法

```python
# 步驟一：生成有效報價報表（前5個時間點）
python step0_valid_quotes.py

# 步驟二：執行 EMA 異常值偵測
python step0_2_ema_calculation.py
```

### 參考文件

- 附錄 3: 選擇權序列價格篩選機制

### 開發狀態

- ✅ Step 0-1: 有效報價驗證
- ✅ Step 0-2: EMA 異常值偵測
- ⏳ Step 0-3: 篩選後報價決定
- ⏳ 後續 VIX 計算步驟

### 技術棧

- Python 3.x
- pandas, numpy
- 自訂訂單簿重建引擎
