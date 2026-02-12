# 臺灣期貨交易所波動率指數 (TAIWAN VIX) - 選擇權序列價格篩選機制 (Series-Level Filtering Algorithm) 技術規格書

## 1. 簡介
本文件依據「臺灣期貨交易所波動率指數_0708.docx」附錄 3 內容及其引用之 Cboe MSCI Volatility Indices 編製方法，定義選擇權序列價格的篩選邏輯。此機制用於在計算 VIX 前，剔除報價異常或流動性不足的選擇權序列，確保指數真實反映市場波動。

## 2. 參數設定 (若文件未更新，以 code 內定值為主)
依據附錄表 7 設定以下參數：

| 參數名稱 | 符號 | 設定值 | 說明 |
| :--- | :---: | :---: | :--- |
| Smoothing Factor | alpha | 0.95 | EMA 平滑係數 |
| Base Gamma | γ0 | 1.20 | 基礎寬容度係數 |
| Bid Improvement Gamma | γ1 | 1.50 | 中價下降時的寬容度係數 |
| Ask Improvement Gamma | γ2 | 2.00 | 中價上升時的寬容度係數 |
| Max Spread | lambda | 15.0 | 最大允許價差 (點數) |

## 3. 資料結構

### 3.1 輸入資料 (Quote)
每筆報價包含以下資訊：
- Time: 報價時間
- Bid: 最佳買價
- Ask: 最佳賣價
- Expiry: 到期月份 (Near-Term 或 Next-Term)
- Strike: 履約價
- Type: 買權 (Call) 或 賣權 (Put)

### 3.2 狀態變數 (State)
針對每個選擇權序列 (Series)，需維護以下狀態：
- EMA_t: 價差的指數移動平均值 (初始為 null)
- Q_hat_t: 經過篩選後決定的最終報價 (包含 Bid, Ask, Mid)

### 3.3 符號慣例 (Notation Convention)
| 符號後綴 | 意義 |
|:---|:---|
| * | 泛指該報價的所有組成部分 (Bid, Ask, Mid, Spread) |
| _Bid | 該報價的買價 |
| _Ask | 該報價的賣價 |
| _Mid | 該報價的中價 = (Bid + Ask) / 2 |
| _Spread | 該報價的價差 = Ask - Bid |
| _t | 當前時間點 t 的數值 |
| _t-1 | 前一個時間點 (t-1) 的數值，來自上一次迭代的結果 |

範例：
- Q_Last_Valid* = 泛指 Q_Last_Valid 這組報價
- Q_Last_Valid_Bid_t = Q_Last_Valid 在時間點 t 的買價
- Q_hat_Mid_t-1 = 上一期篩選後最終報價的中價

## 4. 篩選演算法流程

本演算法針對每一個選擇權序列獨立執行。對於每個時間點 t 的新進報價，執行以下步驟：

### 步驟 1: 獲取有效報價 (Determine Valid Quote)

定義篩選區間為 15 秒。

有效性檢查規則 (Validity Check)：
若報價 Q 滿足以下條件，則視為「有效」 (Valid):
1. Bid 與 Ask 皆為數值 (非 Null)
2. Bid >= 0
3. Ask > Bid

在時間點 t，定義兩個候選報價：

| 符號 | 名稱 | 定義 |
|:---|:---|:---|
| Q_Last_Valid_t | 最近有效報價 | t 時點前最後一筆報價，且已通過有效性檢查。**若無對應報價 (因 PROD Template 補齊)，則為 Null。** |
| Q_Min_Valid_t | 最小價差有效報價 | t 時點前 15 秒內價差最小的報價，且已通過有效性檢查。**若無對應報價，則為 Null。** |

**補齊機制 (Template Filling):**
為確保輸出格式與 PROD 檔案一致，系統會讀取 PROD 檔案中的 Strike 列表作為模板。
對於每個時間點，若某個 Strike x CP 組合在 Raw Data 中無報價，仍會保留該紀錄，其數值 (Bid, Ask, Spread) 皆為 Null。

### 步驟 2: 檢測異常值 (Detect Outliers)

針對 Q_Last_Valid_t 與 Q_Min_Valid_t 各自獨立進行異常值判定。

#### 2.1 計算 EMA (Exponential Moving Average)
使用 Q_Min_Valid_t 的價差 (Spread) 更新 EMA。

EMA 更新公式：
- 若 EMA_t-1 為 null（第一次計算）: EMA_t = Spread(Q_Min_Valid_t)
- 若 Q_Min_Valid_t 為 null（當前無有效報價）: EMA_t = EMA_t-1
- 正常情況: EMA_t = (1 - alpha) * EMA_t-1 + alpha * Spread(Q_Min_Valid_t)
  - 即: EMA_t = 0.05 * EMA_t-1 + 0.95 * Spread(Q_Min_Valid_t)

#### 2.2 決定 Gamma (γ)
Q_Last_Valid_t 與 Q_Min_Valid_t 各自獨立計算 gamma，參考對象為上一期篩選後最終報價 Q_hat_t-1。

以 Q_Last_Valid_t 為例 (Q_Min_Valid_t 以此類推)：

| 條件 | gamma 值 |
|:---|:---:|
| Q_Last_Valid_Bid_t > 0 且 Q_Last_Valid_Mid_t <= Q_hat_Mid_t-1 | γ1 = 1.5 |
| Q_Last_Valid_Bid_t > 0 且 Q_Last_Valid_Mid_t > Q_hat_Mid_t-1 | γ2 = 2.0 |
| Q_Last_Valid_Bid_t = 0 | γ0 = 1.2 |

#### 2.3 異常判定條件
若報價滿足下列任一條件，則不是異常值 (Not Outlier)；否則為異常值 (Outlier)。

以 Q_Last_Valid_t 為例 (Q_Min_Valid_t 以此類推)：

1. Spread(Q_Last_Valid_t) <= gamma(Q_Last_Valid_t) * EMA_t (價差符合 EMA 比例)
2. Spread(Q_Last_Valid_t) < lambda (價差極小，lambda = 15.0)

**缺失資料處理:**
若報價本身為 Null (因 Template 補齊)，則視為 **非異常值 (Not Outlier)**，在 PROD 格式輸出中標記為 `-`。
3. Q_Last_Valid_Bid_t > Q_hat_Mid_t-1 (買價突破上一期中價)
4. Q_Last_Valid_Ask_t < Q_hat_Mid_t-1 且 Q_Last_Valid_Bid_t > 0 (賣價跌破上一期中價)

例外情況：若為當日第一筆資料或 EMA_t-1 為 Null，則 t 時點 Q_Last_Valid_t 與 Q_Min_Valid_t 皆視為非異常值。

### 步驟 3: 決定最終篩選報價 (Determine Filtered Quote)

依據以下優先順序決定 t 時刻的最終報價 Q_hat_t：

1. 優先使用 Q_Last_Valid_t:
   - 若 Q_Last_Valid_t 是 非Null 且 非異常值 -> Q_hat_t = Q_Last_Valid_t

2. 次要使用 Q_Min_Valid_t:
   - 若 Q_Last_Valid_t 為異常值或 Null，但 Q_Min_Valid_t 有雙邊報價且非異常值 -> Q_hat_t = Q_Min_Valid_t

3. 沿用前值:
   - 若上述皆不符合 -> Q_hat_t = Q_hat_t-1 (沿用上一次的結果)

---

## 5. 輸出
演算法對每個序列輸出：
- Filtered_Bid_t (Q_hat_Bid_t)
- Filtered_Ask_t (Q_hat_Ask_t)
- Filtered_Mid_t (Q_hat_Mid_t = (Filtered_Bid_t + Filtered_Ask_t) / 2)

此為 VIX 主計算程序的輸入。

## 6. 待確認事項
1. EMA 公式權重: 已確認 alpha=0.95 作用於當前值 (Spread)，0.05 作用於歷史值 (EMA_t-1)。
2. Gamma 選擇邏輯: 已依文件範例及 Cboe MSCI VIX 標準確認。
3. 時間窗口: 採用 15 秒 Rolling Window (回溯 15 秒取最小價差報價)。建議採用 Rolling Window (回溯 15 秒)。
4. 參數調整 (2026-02-11 更新):
   - 已確認 PROD 環境實際使用的參數為 γ1=1.5, γ2=2.0, lambda=15.0。
   - 文件原設定 (γ1=2.0, γ2=2.5, lambda=0.5) 與 PROD 實際行為不符，已修正本文件以符合 PROD。
