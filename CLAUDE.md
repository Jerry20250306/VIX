# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

台灣期交所 VIX（波動率指數）計算與驗證系統。依照 MSCI 方法論，從原始 tick 資料重建委託簿、計算報價 EMA、偵測異常值，最終算出 VIX 指數，並與官方 PROD 系統輸出做比對驗證。

## Dependencies

```bash
pip install pandas numpy flask
```

No `requirements.txt` — install manually as above.

## Running the Pipeline

### Single day
```bash
python step0_process_quotes.py 20251201
python step1_vix_calc.py --date 20251201
```

### Batch (date range)
```bash
python run_batch.py --start 20251201 --end 20251231
python run_step1_batch.py --start 20251201 --end 20251231
```

### Validation
```bash
python validation/verify_full_day.py 20251201
python validation/verify_step1.py 20251201
```

### Viewer (web dashboard)
```bash
# Windows
.\start_viewer.bat

# Direct (localhost)
python Viewer/app.py

# With network binding
set FLASK_HOST=0.0.0.0 && python Viewer/app.py
```
Viewer auto-selects a free port in range 5100–5199.

## Architecture

### Two-Phase Design

**Phase 1 — Calculation & Verification**

```
Raw tick CSV (資料來源/J002-*/temp/)
  → reconstruct_order_book.py   # 重建委託簿，每日 1200 個快照
  → step0_process_quotes.py     # 報價篩選、EMA(α=0.95)、異常值偵測
      Output: NearPROD_*.tsv, NextPROD_*.tsv
  → validation/verify_full_day.py  # 與 PROD 比對，產生 diff CSV
  → step1_vix_calc.py           # 計算 VIX 指數
      Output: my_sigma_*.tsv, my_ORI_VIX_*.tsv
```

**Phase 2 — Visualization (Viewer/)**

Flask app (`Viewer/app.py`) serves four tabs:
- **Diff Summary** — 與 PROD 的逐欄位差異報告
- **Dashboard** — ECharts 時序趨勢圖（揭示值 vs 計算值）
- **Explorer** — tick 層級委託簿探勘
- **Sigma** — σ 與 VIX 值比較

### Key Modules

| File | Role |
|------|------|
| `vix_utils.py` | `DataPathManager`：資料路徑管理，支援環境變數覆寫 |
| `reconstruct_order_book.py` | 從 tick 流重建委託簿快照 |
| `step0_process_quotes.py` | 報價篩選 + EMA + 異常值偵測 |
| `step1_vix_calc.py` | VIX 指數最終計算 |
| `Viewer/data_loader.py` | `DiffLoader`, `ProdLoader`, `SigmaDiffLoader` |
| `Viewer/tick_parser.py` | `TickLoader`：解析原始 tick 資料 |
| `Viewer/alert_loader.py` | `AlertLoader`：讀取警示報告 |

### Data Paths

- Raw tick data: `資料來源/J002-<id>/temp/*.csv`
- PROD reference: `資料來源/<YYYYMMDD>/`
- Alert reports: `資料來源/Alert/`
- Outputs: `output/`

Override with env vars: `VIX_DATA_SOURCE`, `VIX_PROD_SOURCE`

### Core Algorithm Parameters

- EMA: α = 0.95
- Outlier gamma thresholds: γ₀=1.20, γ₁=1.50, γ₂=2.00
- Max spread: λ = 15 points
- Filter lookback window: 15 seconds
- VIX: MSCI variance swap methodology

## Notes

- All documentation and comments are in Traditional Chinese (繁體中文)
- No database — all data stored as TSV/CSV files
- `Viewer/app.py` supports PyInstaller frozen bundles (`sys.frozen` check)
- VS Code test discovery configured in `.vscode/settings.json` (pattern: `*test.py` in `./Viewer`)
