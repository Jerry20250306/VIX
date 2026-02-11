# VIX 計算專案 (Taiwan VIX Calculation Project)

本專案實作台灣期貨交易所的 VIX (波動率指數) 計算邏輯，並提供完整的驗證與分析工具。

## 📁 目錄結構

- **`step0_valid_quotes.py`**: 核心程式 - 步驟一：有效報價篩選。
- **`step0_2_ema_calculation.py`**: 核心程式 - 步驟二與三：EMA 計算與異常值偵測。
- **`vix_utils.py`**: 共用工具模組，包含資料來源路徑管理。
- **`reconstruct_order_book.py`**: 訂單簿重建邏輯。
- **`validation/`**: 驗證與測試腳本目錄。
  - `verify_full_day.py`: 全天數據完整驗證。
  - `debug_gamma_diff.py`: 針對 Gamma 值差異的除錯工具。
  - `verify_prod_format.py`: 驗證輸出格式是否符合 PROD 要求。
- **`output/`**: 程式執行產出的報表與 CSV 檔案。
  - `驗證報告_*.md`: 自動產生的驗證報告。
  - `欄位對應表.md`: 系統欄位與 PROD 欄位的對照說明。
- **`資料來源/`**: 存放原始行情資料與 PROD 比對資料。

## 🚀 快速開始

### 1. 環境設定

本專案使用 Python 3，請確保已安裝以下套件：

```bash
pip install pandas numpy
```

### 2. 資料來源設定

本系統支援動態偵測資料來源。您不需要修改程式碼中的路徑，從而適應不同的執行環境。

**方式 A：使用預設結構**
將資料放入 `資料來源` 目錄下，系統會自動根據日期尋找：

- Raw Data: `資料來源/J002-xxxxxx_YYYYMMDD/temp` (或類似格式)
- Prod Data: `資料來源/YYYYMMDD` 或 `資料來源/YYYYMMDD_vix`

**方式 B：使用環境變數 (推薦用於不同電腦/環境)**
設定以下環境變數即可覆蓋預設路徑：

- `VIX_DATA_SOURCE`: 指定 Raw Data 的基礎目錄。
- `VIX_PROD_SOURCE`: 指定 PROD Data 的基礎目錄。

### 3. 執行計算

**執行步驟一：有效報價篩選**

```bash
# 預設使用 20251231 資料
python step0_valid_quotes.py

# 指定其他日期
python step0_valid_quotes.py --date 20260101
```

**執行步驟二與三：EMA 計算**

```bash
# 預設使用 20251231 資料
python step0_2_ema_calculation.py

# 指定其他日期
python step0_2_ema_calculation.py 20260101
```

## 🧪 驗證與測試

所有驗證腳本皆位於 `validation/` 目錄中。

### 執行完整流程測試

此腳本會模擬從步驟一到步驟三的完整流程，並與 PROD 資料進行比對，確保計算邏輯正確。

```bash
python validation/test_full_pipeline.py
```

### 驗證路徑解析

測試系統是否能正確抓取當前環境的資料路徑：

```bash
python validation/test_path_resolution.py
```

## 📊 開發狀態

- ✅ **Step 0-1 (有效報價)**: 已完成，邏輯與 PROD 一致。
- ✅ **Step 0-2 (EMA 異常偵測)**: 已完成，邏輯與 PROD 一致。
- ✅ **Step 0-3 (篩選後報價)**: 已完成，邏輯與 PROD 一致。
- ✅ **路徑管理**: 已實作 `get_vix_config` 統一管理，支援動態路徑。

## 📝 參考文件

- `spec.md`: 選擇權序列價格篩選機制技術規格。
- `walkthrough.md`: 最近一次的重構與驗證紀錄。
