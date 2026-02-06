
# VIX 計算模組實作任務清單

## 第一階段：委託簿重建 (當前重點)
- [x] 分析「選擇權序列價格篩選機制」邏輯 <!-- id: 5 -->
    - [x] 重讀 `選擇權序列價格篩選機制.docx` 以確認細部規則 <!-- id: 6 -->
    - [x] 定義「快照對應 Tick」的匹配演算法 (確認為 15秒內最小價差) <!-- id: 7 -->
- [ ] 設計資料處理流程 <!-- id: 8 -->
    - [x] 定義原始行情資料 (Ticks) 的格式 <!-- id: 9 -->
    - [x] 確認商品代號 (Product ID) 解析規則 <!-- id: 21 -->
    - [x] 確認快照觸發源 (Trigger Source) 為 NearPROD/NextPROD <!-- id: 22 -->
    - [x] 設計 `QuoteFilter` 類別 (實作篩選規則) <!-- id: 10 -->
    - [x] 設計 `SnapshotBuilder` 類別 (重建 PROD 檔案) <!-- id: 11 -->
        - [x] 實作讀取 PROD 檔取得 Snapshot_SysID 列表 <!-- id: 23 -->
        - [x] 實作依月份過濾 Near/Next 商品邏輯 <!-- id: 24 -->
        - [x] 驗證重建結果 (My_Min vs Official 完美匹配) <!-- id: 25 -->

## 第二階段：VIX 計算邏輯 (待辦)
- [x] 從文件研究 VIX 計算邏輯 <!-- id: 0 -->
    - [x] 讀取 `4.13_附件4   臺灣期貨交易所波動率指數_0708.docx` <!-- id: 1 -->
    - [x] 分析計算步驟與公式 <!-- id: 2 -->
    - [x] 確認 `Near_Forward` 包含預先計算的遠期價格 <!-- id: 4 -->
- [ ] 實作資料讀取器 (Loader) <!-- id: 12 -->
    - [ ] 實作讀取 `NearPROD` / `NextPROD` <!-- id: 13 -->
    - [ ] 實作讀取 `Near_Forward` / `rate` <!-- id: 14 -->
- [ ] 實作 VIX 計算核心 (Calculator) <!-- id: 15 -->
    - [ ] 實作序列價格篩選 (Step 0) <!-- id: 26 -->
        - [x] 步驟一：獲取有效報價與驗證 (Valid Quote Check) <!-- id: 27 -->
        - [x] 步驟二：異常值偵測 (Outlier Detection via EMA) <!-- id: 28 -->
        - [ ] 步驟三：篩選後報價決定 (Filtered Quote Priority Logic) <!-- id: 29 -->
    - [ ] 實作有效履約價篩選 ($K_0$) <!-- id: 16 -->
    - [ ] 實作插補與 VIX 公式 <!-- id: 17 -->
- [ ] 驗證結果 (Verifier) <!-- id: 18 -->
    - [ ] 與 `Near_Contrib` 比對單一序列貢獻度 <!-- id: 19 -->
    - [ ] 與 `ORI_VIX` 比對最終結果 <!-- id: 20 -->

## 專案維護 (Project Maintenance)
- [x] 安裝 Git 環境
- [/] 推送專案至 GitHub (執行中)
