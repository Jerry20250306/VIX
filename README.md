# VIX 計算專案 (Taiwan VIX Calculation Project)

本專案實作台灣期貨交易所的 VIX (波動率指數) 計算邏輯，並提供完整的驗證與分析工具。

## 📁 目錄結構

- **`step0_process_quotes.py`**: 核心程式 - 整合有效報價篩選、EMA 計算與異常值偵測 (Step 0 全流程)。
- **`step1_vix_calc.py`**: 核心程式 - VIX 指數計算。
- **`run_batch.py`**: 批次執行工具，支援指定日期範圍自動跑完處理與驗證。
- **`vix_utils.py`**: 共用工具模組，包含資料來源路徑管理。
- **`reconstruct_order_book.py`**: 訂單簿重建邏輯。
- **`validation/`**: 驗證與測試腳本目錄。
  - `verify_full_day.py`: 全天數據完整驗證。
  - `debug_gamma_diff.py`: 針對 Gamma 值差異的除錯工具。
  - `verify_prod_format.py`: 驗證輸出格式是否符合 PROD 要求。
- **`output/`**: 程式執行產出的數據與比較檔案。
  - `NearPROD_*.tsv` / `NextPROD_*.tsv`: 模擬官方格式的報價處理結果。
  - `validation_diff_*.csv`: 由驗證系統產出的詳細差異報告。
  - `my_sigma_*.tsv`: 最終計算出的 VIX 指數。
- **`資料來源/`**: 存放原始行情資料與 PROD 比對資料。

## 🚀 快速開始

### 1. 環境設定

本專案使用 Python 3，請確保已安裝以下套件：

```bash
pip install pandas numpy flask
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

#### 步驟 0：報價處理與異常值偵測 (整合版)

```bash
# 執行單日處理 (預設會還原全天 1200 個時間點並計算 EMA/Outlier)
python step0_process_quotes.py 20251201
```

#### 步驟 1：VIX 指數計算

```bash
# 根據步驟 0 的產出計算最終 VIX 值
python step1_vix_calc.py --date 20251201
```

#### **批次執行 (處理 + 自動驗證)**

除了單日分別執行外，您可以透過批次腳本一鍵跑完指定跨度：

```bash
# 單日處理與驗證 (推薦用法：處理完自動產出差異報告)
python run_batch.py --date 20251201

# 一段期間的批次處理與驗證 (Step 0)
python run_batch.py --start 20251201 --end 20251231

# 一段期間的批次處理與驗證 (Step 1)
python run_step1_batch.py --start 20251201 --end 20251231
```

## 🔍 視覺化檢視工具

本專案提供網頁版的視覺化檢視工具 (Viewer)，方便您直觀地分析計算結果與 PROD 之間的差異。

### 啟動方式

**Windows 推薦 (支援區域網路連線):**

```bash
# 直接執行批次檔即可
.\start_viewer.bat
```

**手動指令:**

```bash
# 本機使用
python Viewer/app.py

# 供區域網路其它電腦連線 (指定 Host)
$env:FLASK_HOST="0.0.0.0"; python Viewer/app.py
```

### 主要功能

- **差異摘要 (Diff Summary)**：自動掃描 `output/` 下的驗證報告，列出所有不一致的點。
- **逐筆分析**：點擊差異點可查看該時點的原始報價、計算過程與 PROD 數據。
- **VIX 曲線比對**：視覺化對照自研計算結果與官方 VIX 數值的走勢差異。
- **Tick 追蹤**：回溯快照生成時的原始 Tick 來源。

所有驗證腳本皆位於 `validation/` 目錄中，用於確保計算結果與官方 PROD 資料 100% 一致。

### 全天數據比對 (PROD Parity)

如果您已經執行完 `step0_process_quotes.py`，可以使用此腳本進行細節比對並產出差異報告：

```bash
# 語法：python validation/verify_full_day.py [日期]
python validation/verify_full_day.py 20251201
```

> **注意**：
>
> 1. 您必須輸入日期（如 `20251201`），系統才能找到對應的輸出檔案進行比對。
> 2. 產出的差異報告會存放在 `output/validation_diff_YYYYMMDD.csv`。
> 3. 推薦直接使用 `run_batch.py --date [日期]`，它會自動跑完處理並觸發此驗證。

### Step 1 指數量化比對

如果您已經執行完 `step1_vix_calc.py` 產出 `my_sigma_YYYYMMDD.tsv`，可使用此腳本比對包含變異數與 VIX 重點數值：

```bash
# 語法：python validation/verify_step1.py [日期]
python validation/verify_step1.py 20251201
```

### 關於「步驟」的說明

本專案遵循兩大階段設計：
- **Step 0 (`step0_process_quotes.py`)**: 報價處理階段。整合了「有效報價篩選」、「EMA 平均價計算」與「異常值偵測」。這是產生 VIX 計算基準的最關鍵步驟。
- **Step 1 (`step1_vix_calc.py`)**: 正式計算階段。根據 Step 0 產出的過濾報價，計算最終的 TAIWAN VIX 指數。

## 📊 開發狀態

- ✅ **Step 0 (報價處理整合)**: 已完成，產出與官方 PROD 高度一致的基準報價。
- ✅ **Step 1 (VIX 指數正式計算)**: 已完成，修正時間單位換算，支援小數點揭示與退化插補條件。
- ✅ **自動化驗證機制**: 已加入 `run_batch.py` 與 `run_step1_batch.py`，支援全月精準對照。
- ✅ **路徑管理**: 已實作 `get_vix_config` 統一管理，支援各環境動態路徑。

## 📁 文件索引 (Documentation)

所有的技術文件皆已整合至 `docs/` 目錄下：

### 📚 規格書 (Specs)

- **[演算法邏輯與參數](docs/規格書/演算法邏輯與參數.md)**: 包含核心參數、價格篩選邏輯、EMA 計算、以及委託簿重建機制。
- **[驗證規則與對照](docs/規格書/驗證規則與對照.md)**: 包含 PROD 檔案格式、欄位對照表、以及驗證方法。
- **[檢視工具說明](docs/規格書/檢視工具說明.md)**: 說明如何使用 `Viewer/` 下的視覺化工具。

### 📖 參考資料 (References)

- **[官方編製方法](docs/參考資料/官方編製方法.md)**: 台灣期貨交易所原始文件。
- **[官方附錄文件](docs/參考資料/官方附錄文件.docx)**: 包含參數設定的原始 Word 檔。

### 🛠️ 專案管理 (Project Management)

- **[執行計畫](docs/專案管理/執行計畫.md)**: 當前的開發計畫與進度。
- **[任務列表](docs/專案管理/任務列表.md)**: 詳細的待辦事項清單。
- **[開發歷程](docs/專案管理/開發歷程.md)**: 專案的演進與重大變更紀錄。
