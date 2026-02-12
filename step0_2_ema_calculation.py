"""
================================================================================
Step 0 步驟二與步驟三：異常值偵測 + 篩選後報價決定
(Outlier Detection via EMA + Determine Filtered Quote)

依據「臺灣期貨交易所波動率指數」附錄 3 與 spec.md 實作
================================================================================

【本模組功能說明】
此模組實作 VIX 計算前的「序列價格篩選機制」的步驟二與步驟三：

步驟二 (Outlier Detection)：
  - 2.1 計算 EMA（指數移動平均）
  - 2.2 決定 Gamma 參數
  - 2.3 判定報價是否為異常值

步驟三 (Determine Filtered Quote)：
  - 依優先順序決定最終篩選報價 Q_hat

【術語對照表】
  - Q_Last_Valid: 最近一筆有效報價（已通過有效性檢查）
  - Q_Min_Valid:  15 秒內價差最小的有效報價（已通過有效性檢查）
  - Q_hat:        最終篩選後決定的報價（步驟三的輸出）
  - EMA:          指數移動平均（Exponential Moving Average）
  - Gamma (γ):    異常值判定的寬容度係數
  - Lambda (λ):   最大允許價差門檻（15 點）

【符號後綴說明】
  - _t:    表示「當前時間點」的數值
  - _t-1:  表示「前一個時間點」的數值（上一次迭代結果）
  - _Bid:  買價
  - _Ask:  賣價
  - _Mid:  中價 = (Bid + Ask) / 2
  - _Spread: 價差 = Ask - Bid
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os


# ==============================================================================
# 全域參數設定（依據 spec.md 表 7）
# ==============================================================================

ALPHA = 0.95    # EMA 平滑係數（歷史 EMA 權重為 95%，當前價差的權重為 5%）
GAMMA_0 = 1.2   # 基礎寬容度：當 Bid = 0 時使用（例如：深度價外選擇權）
GAMMA_1 = 1.5   # 中價下降寬容度：當 Bid > 0 且 Mid_t <= Q_hat_Mid_t-1 時使用
GAMMA_2 = 2.0   # 中價上升寬容度：當 Bid > 0 且 Mid_t > Q_hat_Mid_t-1 時使用
LAMBDA = 15      # 最大允許價差（點數）：Spread < 15 點一律視為非異常值


# ==============================================================================
# 輔助函式
# ==============================================================================

def is_valid_value(val):
    """
    檢查值是否為「有效值」（非 null、非空白、非 NaN）
    
    【用途說明】
    在 VIX 計算中，報價可能因為無成交或無掛單而呈現 null/NaN/空白，
    此函式用來統一判斷這類「無效」情況。
    
    【範例】
    is_valid_value(100.5)   → True  （有效數值）
    is_valid_value("null")  → False （字串 null）
    is_valid_value(None)    → False （Python None）
    is_valid_value(np.nan)  → False （NaN）
    is_valid_value("")      → False （空字串）
    
    Args:
        val: 要檢查的值（可為數值、字串、None 等）
        
    Returns:
        bool: True 表示有效，False 表示無效
    """
    return val is not None and val != "null" and val != "" and not pd.isna(val)


def has_two_sided_quote(bid, ask):
    """
    檢查是否為「雙邊報價」（Bid 和 Ask 都有有效值）
    
    【用途說明】
    在步驟三決定最終報價時，必須確認報價是「雙邊」的，
    也就是買價和賣價都存在，才能用來計算中價。
    
    【範例】
    has_two_sided_quote(100, 102)    → True  （雙邊有報價）
    has_two_sided_quote(100, "null") → False （賣價無效）
    has_two_sided_quote(0, 102)      → True  （Bid=0 也算有效，表示深度價外）
    
    Args:
        bid: 買價
        ask: 賣價
        
    Returns:
        bool: True 表示為雙邊報價，False 表示非雙邊報價
    """
    return is_valid_value(bid) and is_valid_value(ask)


# ==============================================================================
# 步驟 2.1：EMA 計算
# ==============================================================================

def calculate_ema_for_series(time_series_df):
    """
    為單個選擇權序列（相同 Strike + CP）計算所有時間點的 EMA
    
    【EMA 公式說明】
    EMA（指數移動平均）用於追蹤價差的歷史趨勢，公式如下：
    
    1. 若 EMA_t-1 為 null（第一次計算）：
       EMA_t = Q_Min_Valid_Spread_t
       （直接使用第一筆有效的價差作為初始值）
    
    2. 若 Q_Min_Valid_t 為 null（當前無有效報價）：
       EMA_t = EMA_t-1
       （維持上一期的 EMA 不變）
    
    3. 正常情況：
       EMA_t = 0.95 × EMA_t-1 + 0.05 × Q_Min_Valid_Spread_t
       （歷史權重 95%，新價差權重 5%，使 EMA 平滑緩慢變化）
    
    【白話範例】
    假設前三個時間點的價差分別為 1.0、1.2、1.5：
    - t=0: EMA = 1.0（初始值，直接使用第一筆）
    - t=1: EMA = 0.95×1.0 + 0.05×1.2 = 0.95 + 0.06 = 1.01
    - t=2: EMA = 0.95×1.01 + 0.05×1.5 = 0.9595 + 0.075 = 1.0345
    
    Args:
        time_series_df: 該序列（Strike + CP）的所有時間點資料，需包含：
            - Time (字串，例如 '084500')
            - Q_Min_Valid_Spread (有效時為數值，無效時為 "null")
            
    Returns:
        DataFrame: 新增 EMA 和 EMA_Process 欄位的 DataFrame
    """
    # 複製資料並按時間排序（確保迭代順序正確）
    df = time_series_df.sort_values('Time').copy()
    
    # 【優化】預先取出 spread 和 time 為 Python list，避免 pandas 迭代開銷
    spreads = df['Q_Min_Valid_Spread'].tolist()
    times = df['Time'].tolist()
    n = len(spreads)
    
    # 09:00:00 正式開盤時間（盤前 08:45~09:00 的 EMA 歷史不帶入）
    # Time 欄位可能是 int(90000) 或 str('090000')，兩種都檢查
    MARKET_OPEN_TIMES = {90000, '90000', '090000'}
    
    # 【優化】使用 list 收集結果，最後一次賦值到 DataFrame
    ema_list = [None] * n
    process_list = [None] * n
    
    # 追蹤前一時點的 EMA（用於遞迴計算）
    prev_ema = None
    
    # 逐筆迭代計算 EMA
    for i in range(n):
        spread = spreads[i]
        
        # 【09:00 重置】正式開盤時，清除盤前 EMA 歷史
        if times[i] in MARKET_OPEN_TIMES:
            prev_ema = None
        
        # 檢查價差是否為 null（無有效報價）
        is_null = (spread == "null" or pd.isna(spread))
        
        # [移除 Fallback] 嚴格遵守 Spec：EMA 只使用 Q_Min_Valid_Spread
        # 如果 Q_Min 為 null，EMA 維持不變（或初始化為 null）
            
        if prev_ema is None:
            if is_null:
                # 第一筆就沒有有效報價 → EMA 也設為 null
                ema = "null"
                process = "初始值：Q_Min/Q_Last 為 null → EMA = null"
            else:
                # 第一筆有有效報價 → 直接用該價差作為 EMA 初始值
                ema = float(spread)
                process = f"初始值：EMA_0 = Spread = {spread}"
        else:
            # ===== 有前一時點的 EMA =====
            if prev_ema == "null":
                # 前一時點 EMA 為 null
                if is_null:
                    # 前面和現在都沒有有效報價 → 繼續維持 null
                    ema = "null"
                    process = "EMA_t-1 為 null，Q_Min/Q_Last 也為 null → EMA_t = null"
                else:
                    # 前面沒有但現在有 → 用現在的價差作為新的 EMA 起點
                    ema = float(spread)
                    process = f"EMA_t-1 為 null → EMA_t = Spread = {spread}"
            else:
                # 前一時點 EMA 有有效值
                if is_null:
                    # ===== 情況 2：當前無有效報價 → EMA 維持不變 =====
                    ema = prev_ema
                    process = f"Q_Min/Q_Last 為 null → EMA_t = EMA_t-1 = {prev_ema:.6f}"
                else:
                    # ===== 情況 3：正常計算 =====
                    # EMA_t = alpha × EMA_t-1 + (1 - alpha) × Spread_t
                    #       = 0.95 × EMA_t-1 + 0.05 × Spread_t
                    ema = ALPHA * prev_ema + (1 - ALPHA) * float(spread)
                    process = f"正常公式：EMA_t = 0.95×{prev_ema:.6f} + 0.05×{spread} = {ema:.6f}"
        
        # 【優化】寫入 list 而非 df.at（減少 pandas 開銷）
        ema_list[i] = ema
        process_list[i] = process
        
        # 更新 prev_ema 供下一次迭代使用
        prev_ema = ema
    
    # 【優化】一次性賦值到 DataFrame
    df['EMA'] = ema_list
    df['EMA_Process'] = process_list
    
    return df


# ==============================================================================
# 步驟 2.2：決定 Gamma 參數
# ==============================================================================

def determine_gamma(current_bid, current_mid, Q_hat_Mid_t_minus_1):
    """
    根據當前報價與前一時點篩選後報價的中價，決定 Gamma (γ) 參數
    
    【Gamma 參數說明】
    Gamma 是異常值判定的「寬容度係數」，用於與 EMA 相乘形成門檻。
    Gamma 越大，容許的價差範圍越寬鬆。
    
    【選擇邏輯】（依據 spec.md 2.2）
    
    1. 若 Bid_t = 0：γ = γ0 = 1.2
       - 意義：Bid = 0 表示深度價外選擇權，流動性差，使用較嚴格的門檻
       
    2. 若 Bid_t > 0 且 Mid_t <= Q_hat_Mid_t-1：γ = γ1 = 2.0
       - 意義：中價沒有上漲（維持或下跌），使用中等寬容度
       
    3. 若 Bid_t > 0 且 Mid_t > Q_hat_Mid_t-1：γ = γ2 = 2.5
       - 意義：中價上漲，可能是市場波動，使用較寬鬆的門檻
    
    【白話範例】
    假設前一期 Q_hat_Mid_t-1 = 50，當前報價：
    - Bid=0, Ask=100 → γ = 1.2（深度價外）
    - Bid=48, Ask=52, Mid=50 → 50 <= 50 → γ = 2.0（中價持平）
    - Bid=52, Ask=56, Mid=54 → 54 > 50 → γ = 2.5（中價上漲）
    
    Args:
        current_bid: 當前報價的買價
        current_mid: 當前報價的中價
        Q_hat_Mid_t_minus_1: 前一時點篩選後最終報價的中價
        
    Returns:
        tuple: (gamma 值, 判斷過程說明字串)
    """
    # ----- 檢查當前 Bid 是否為 null -----
    if not is_valid_value(current_bid):
        return GAMMA_0, f"Bid_t 為 null → γ = γ₀ = {GAMMA_0}"
    
    bid_val = float(current_bid)
    
    # ----- 情況 1：Bid = 0（深度價外選擇權）-----
    if bid_val == 0:
        return GAMMA_0, f"Bid_t = 0 → γ = γ₀ = {GAMMA_0}"
    
    # ----- Bid > 0，需進一步比較 Mid -----
    
    # 檢查 Mid 是否有效
    if not is_valid_value(current_mid):
        return GAMMA_0, f"Bid_t = {bid_val} > 0，但 Mid_t 為 null → γ = γ₀ = {GAMMA_0}"
    
    # 檢查前一時點的 Q_hat_Mid 是否有效
    if not is_valid_value(Q_hat_Mid_t_minus_1):
        # 第一筆資料（如 084515）或前面沒有篩選結果 → 使用 γ₂（2.0）符合 PROD 行為
        return GAMMA_2, f"Bid_t = {bid_val} > 0，但 Q_hat_Mid_t-1 為 null（可能是第一筆 084515）→ γ = γ₂ = {GAMMA_2}"
    
    mid_val = float(current_mid)
    prev_mid_val = float(Q_hat_Mid_t_minus_1)
    
    # ----- 情況 2：Mid_t <= Q_hat_Mid_t-1（中價持平或下跌）-----
    # 注意：加入浮點數容差 (1e-9)，避免微小誤差導致誤判為上漲 (如 4.80000...01 > 4.8)
    if mid_val <= prev_mid_val + 1e-9:
        return GAMMA_1, f"Bid_t = {bid_val} > 0 且 Mid_t({mid_val}) <= Q_hat_Mid_t-1({prev_mid_val}) → γ = γ₁ = {GAMMA_1}"
    
    # ----- 情況 3：Mid_t > Q_hat_Mid_t-1（中價上漲）-----
    else:
        return GAMMA_2, f"Bid_t = {bid_val} > 0 且 Mid_t({mid_val}) > Q_hat_Mid_t-1({prev_mid_val}) → γ = γ₂ = {GAMMA_2}"


# ==============================================================================
# 步驟 2.3：異常值判定
# ==============================================================================

def check_outlier(spread, bid, ask, ema_t, gamma, Q_hat_Mid_t_minus_1):
    """
    檢查報價是否為異常值 (Outlier)
    
    【判定邏輯說明】（依據 spec.md 2.3）
    
    報價只要符合「任一條件」，就視為「非異常值」：
    
    Condition 1: Spread <= γ × EMA_t
        - 價差在 EMA 的合理倍數範圍內
        - 例：EMA=1.0, γ=2.0 → Spread <= 2.0 即為非異常
        
    Condition 2: Spread < λ (λ = 0.5)
        - 價差極小（小於 0.5 點），一律視為正常
        - 例：Spread=0.3 < 0.5 → 非異常
        
    Condition 3: Bid_t > Q_hat_Mid_t-1
        - 買價突破上一期的中價（強勢買盤）
        - 例：Q_hat_Mid=50, Bid=52 → 52 > 50 → 非異常
        
    Condition 4: Ask_t < Q_hat_Mid_t-1 且 Bid_t > 0
        - 賣價跌破上一期的中價（強勢賣盤）
        - 例：Q_hat_Mid=50, Ask=48, Bid=45 → 48 < 50 且 45 > 0 → 非異常
    
    【例外情況】
    - 若 Q_hat_Mid_t-1 為 null（第一筆資料），一律視為非異常值
    - 若報價本身為 null，也視為非異常值（無需判定）
    
    Args:
        spread: 當前報價的價差 (Ask - Bid)
        bid: 當前報價的買價
        ask: 當前報價的賣價
        ema_t: 當前時點的 EMA
        gamma: 該報價對應的 γ 參數
        Q_hat_Mid_t_minus_1: 前一時點篩選後最終報價的中價
        
    Returns:
        tuple: (is_outlier, reason, cond_1, cond_2, cond_3, cond_4, cond_5, cond_6)
            - is_outlier: True=異常值, False=非異常值
            - reason: 判定原因說明
            - cond_1~4: 各條件是否通過
            - cond_5: 例外情況 2（第一筆資料/Q_hat_Mid_t-1 為 null）
            - cond_6: 例外情況 3（EMA 為 null）
    """
    # 初始化所有條件狀態為 False
    cond_1 = False
    cond_2 = False
    cond_3 = False
    cond_4 = False
    cond_5 = False
    cond_6 = False
    
    # ===== 例外情況 1：報價本身為 null =====
    # 若 Spread/Bid/Ask 皆為無效，視為無資料 (None)
    if not is_valid_value(spread) and not is_valid_value(bid) and not is_valid_value(ask):
        return None, "報價為 null → 無資料", False, False, False, False, False, False
    
    # ===== 例外情況 3：EMA_t-1 為 null → 填入 6 =====
    # [修正順序] 先檢查 EMA，因為 PROD 優先報告 EMA 為 null (6)
    if not is_valid_value(ema_t):
        return False, "EMA_t-1 為 null → 視為非異常值", False, False, False, False, False, True
        
    # ===== 例外情況 2：Q_hat_Mid_t-1 為 null（第一筆資料）→ 填入 5 =====
    if not is_valid_value(Q_hat_Mid_t_minus_1):
        return False, "Q_hat_Mid_t-1 為 null（第一筆資料）→ 視為非異常值", False, False, False, False, True, False
    
    # 轉換為數值進行比較
    spread_val = float(spread)
    prev_mid_val = float(Q_hat_Mid_t_minus_1)
    
    # ===== Condition 1：Spread <= γ × EMA_t =====
    if is_valid_value(ema_t):
        ema_t_val = float(ema_t)
        threshold_1 = gamma * ema_t_val
        if spread_val <= threshold_1:
            cond_1 = True
    
    # ===== Condition 2：Spread <= λ =====
    if spread_val <= LAMBDA:
        cond_2 = True
    
    # ===== Condition 3 & 4 需要 Bid 和 Ask =====
    if is_valid_value(bid):
        bid_val = float(bid)
        
        # ----- Condition 3：Bid_t > Q_hat_Mid_t-1（買價突破上一期中價）-----
        if bid_val > prev_mid_val:
            cond_3 = True
        
        # ----- Condition 4：Ask_t < Q_hat_Mid_t-1 且 Bid_t > 0（賣價跌破上一期中價）-----
        if is_valid_value(ask):
            ask_val = float(ask)
            if ask_val < prev_mid_val and bid_val > 0:
                cond_4 = True
    
    # ===== 統一判定：任一條件通過即為非異常值 =====
    if cond_1 or cond_2 or cond_3 or cond_4:
        # 組合所有通過的條件編號
        passed = []
        if cond_1:
            passed.append("1")
        if cond_2:
            passed.append("2")
        if cond_3:
            passed.append("3")
        if cond_4:
            passed.append("4")
        reason = f"Condition {','.join(passed)} 通過 → 非異常值"
        return False, reason, cond_1, cond_2, cond_3, cond_4, cond_5, cond_6
    
    # ===== 不符合任一條件 → 判定為異常值 =====
    return True, "不符合任一非異常值條件 → 判定為異常值", cond_1, cond_2, cond_3, cond_4, cond_5, cond_6


# ==============================================================================
# 主要處理函式：整合步驟二與步驟三
# ==============================================================================

def add_ema_and_outlier_detection(df, term_name):
    """
    為整個 Term（Near 或 Next）的所有序列執行步驟二與步驟三
    
    【處理流程】
    1. 為每個序列（Strike + CP）計算 EMA
    2. 為 Q_Last_Valid 和 Q_Min_Valid 各自決定 Gamma
    3. 為 Q_Last_Valid 和 Q_Min_Valid 各自判定是否為異常值
    4. 依優先順序決定最終篩選報價 Q_hat
    
    【步驟三優先順序】（依據 spec.md）
    優先順序 1：若 Q_Last_Valid_t 有雙邊報價且非異常值 → 使用 Q_Last_Valid_t
    優先順序 2：若 Q_Min_Valid_t 有雙邊報價且非異常值 → 使用 Q_Min_Valid_t
    優先順序 3：沿用前值 Q_hat_t-1
    
    Args:
        df: 包含所有時間點的資料，需先經過步驟一產生 Q_*_Valid_* 欄位
        term_name: 'Near' 或 'Next'
        
    Returns:
        DataFrame: 新增 EMA、Gamma、異常值判定、Q_hat_* 等欄位
    """
    # ===== 第一階段：為每個序列計算 EMA =====
    all_series = []
    
    for (strike, cp), group in df.groupby(['Strike', 'CP'], sort=False):
        print(f"  處理序列: Strike={strike}, CP={cp}")
        series_df = calculate_ema_for_series(group)
        all_series.append(series_df)
    
    # 合併所有序列
    result_df = pd.concat(all_series, ignore_index=True)
    
    # ===== 初始化步驟二輸出欄位 =====
    
    # Gamma 相關欄位
    result_df['Q_Last_Valid_Gamma'] = None    # Q_Last_Valid 對應的 γ 值
    result_df['Q_Min_Valid_Gamma'] = None     # Q_Min_Valid 對應的 γ 值
    result_df['Gamma_Process'] = None         # Gamma 判斷過程說明
    
    # Q_Last_Valid 異常值判定結果
    result_df['Q_Last_Valid_Is_Outlier'] = None      # 是否為異常值
    result_df['Q_Last_Valid_Outlier_Reason'] = None  # 判定原因
    result_df['Q_Last_Valid_Cond_1'] = None          # Condition 1 是否通過
    result_df['Q_Last_Valid_Cond_2'] = None          # Condition 2 是否通過
    result_df['Q_Last_Valid_Cond_3'] = None          # Condition 3 是否通過
    result_df['Q_Last_Valid_Cond_4'] = None          # Condition 4 是否通過
    result_df['Q_Last_Valid_Cond_5'] = None          # 例外 2：第一筆資料
    result_df['Q_Last_Valid_Cond_6'] = None          # 例外 3：EMA 為 null
    
    # Q_Min_Valid 異常值判定結果
    result_df['Q_Min_Valid_Is_Outlier'] = None       # 是否為異常值
    result_df['Q_Min_Valid_Outlier_Reason'] = None   # 判定原因
    result_df['Q_Min_Valid_Cond_1'] = None           # Condition 1 是否通過
    result_df['Q_Min_Valid_Cond_2'] = None           # Condition 2 是否通過
    result_df['Q_Min_Valid_Cond_3'] = None           # Condition 3 是否通過
    result_df['Q_Min_Valid_Cond_4'] = None           # Condition 4 是否通過
    result_df['Q_Min_Valid_Cond_5'] = None           # 例外 2：第一筆資料
    result_df['Q_Min_Valid_Cond_6'] = None           # 例外 3：EMA 為 null
    
    # ===== 初始化步驟三輸出欄位 =====
    result_df['Q_hat_Bid'] = None     # 最終篩選報價的買價
    result_df['Q_hat_Ask'] = None     # 最終篩選報價的賣價
    result_df['Q_hat_Mid'] = None     # 最終篩選報價的中價
    result_df['Q_hat_Source'] = None  # 報價來源：'Q_Last_Valid'、'Q_Min_Valid'、'Replacement'
    
    # 按 Strike、CP、Time 排序（確保時間序列正確）
    result_df = result_df.sort_values(['Strike', 'CP', 'Time']).reset_index(drop=True)
    
    # ===== 第二階段：逐序列判定異常值並決定 Q_hat =====
    
    for (strike, cp), group_indices in result_df.groupby(['Strike', 'CP'], sort=False).groups.items():
        
        # 追蹤前一時點的 Q_hat（用於 Gamma 決定和異常值判定）
        Q_hat_Bid_prev = None
        Q_hat_Ask_prev = None
        Q_hat_Mid_prev = None
        
        for i, idx in enumerate(group_indices):
            row = result_df.loc[idx]
            
            # 【09:00:00 重置】正式開盤時，清除盤前 Q_hat 歷史
            # 與 EMA 重置同步，讓 Gamma 判定視為第一筆（Q_hat_Mid_prev = None → gamma = 2.0）
            current_time = row['Time']
            MARKET_OPEN_TIMES = {90000, '90000', '090000'}
            if current_time in MARKET_OPEN_TIMES:
                Q_hat_Bid_prev = None
                Q_hat_Ask_prev = None
                Q_hat_Mid_prev = None
            
            # 取得當前 EMA
            current_ema = row['EMA']
            
            # ----- 取得 Q_Last_Valid 資訊 -----
            Q_Last_Valid_Spread = row['Q_Last_Valid_Spread']
            Q_Last_Valid_Bid = row['Q_Last_Valid_Bid']
            Q_Last_Valid_Ask = row['Q_Last_Valid_Ask']
            Q_Last_Valid_Mid = row['Q_Last_Valid_Mid']
            
            # ----- 取得 Q_Min_Valid 資訊 -----
            Q_Min_Valid_Spread = row['Q_Min_Valid_Spread']
            Q_Min_Valid_Bid = row['Q_Min_Valid_Bid']
            Q_Min_Valid_Ask = row['Q_Min_Valid_Ask']
            Q_Min_Valid_Mid = row['Q_Min_Valid_Mid']
            
            # ===== 步驟 2.2：決定 Gamma =====
            
            # 為 Q_Last_Valid 決定 gamma
            gamma_last, gamma_last_process = determine_gamma(
                Q_Last_Valid_Bid, Q_Last_Valid_Mid, Q_hat_Mid_prev
            )
            result_df.at[idx, 'Q_Last_Valid_Gamma'] = gamma_last
            
            # 為 Q_Min_Valid 決定 gamma
            gamma_min, gamma_min_process = determine_gamma(
                Q_Min_Valid_Bid, Q_Min_Valid_Mid, Q_hat_Mid_prev
            )
            result_df.at[idx, 'Q_Min_Valid_Gamma'] = gamma_min
            result_df.at[idx, 'Gamma_Process'] = gamma_min_process
            
            # [修正] 決定最終報告的 Gamma (Reported Gamma)
            # PROD 似乎優先報告 Q_Min 的 Gamma (若 Q_Min 存在)，即使它是 Outlier
            # 例：084530 Strike 27400 Put，Q_Min Gamma=1.5, Q_Last Gamma=2.0，PROD 報告 1.5
            if is_valid_value(Q_Min_Valid_Bid) and is_valid_value(gamma_min):
                 result_df.at[idx, 'Q_Last_Valid_Gamma'] = gamma_min
            else:
                 result_df.at[idx, 'Q_Last_Valid_Gamma'] = gamma_last
            
            # ===== 步驟 2.3：判定異常值 =====
            
            # 判定 Q_Last_Valid 是否為異常值
            is_outlier_last, reason_last, cond_1_last, cond_2_last, cond_3_last, cond_4_last, cond_5_last, cond_6_last = check_outlier(
                Q_Last_Valid_Spread, Q_Last_Valid_Bid, Q_Last_Valid_Ask,
                current_ema, gamma_last, Q_hat_Mid_prev
            )
            result_df.at[idx, 'Q_Last_Valid_Is_Outlier'] = is_outlier_last
            result_df.at[idx, 'Q_Last_Valid_Outlier_Reason'] = reason_last
            result_df.at[idx, 'Q_Last_Valid_Cond_1'] = cond_1_last
            result_df.at[idx, 'Q_Last_Valid_Cond_2'] = cond_2_last
            result_df.at[idx, 'Q_Last_Valid_Cond_3'] = cond_3_last
            result_df.at[idx, 'Q_Last_Valid_Cond_4'] = cond_4_last
            result_df.at[idx, 'Q_Last_Valid_Cond_5'] = cond_5_last
            result_df.at[idx, 'Q_Last_Valid_Cond_6'] = cond_6_last
            
            # 判定 Q_Min_Valid 是否為異常值
            is_outlier_min, reason_min, cond_1_min, cond_2_min, cond_3_min, cond_4_min, cond_5_min, cond_6_min = check_outlier(
                Q_Min_Valid_Spread, Q_Min_Valid_Bid, Q_Min_Valid_Ask,
                current_ema, gamma_min, Q_hat_Mid_prev
            )
            result_df.at[idx, 'Q_Min_Valid_Is_Outlier'] = is_outlier_min
            result_df.at[idx, 'Q_Min_Valid_Outlier_Reason'] = reason_min
            result_df.at[idx, 'Q_Min_Valid_Cond_1'] = cond_1_min
            result_df.at[idx, 'Q_Min_Valid_Cond_2'] = cond_2_min
            result_df.at[idx, 'Q_Min_Valid_Cond_3'] = cond_3_min
            result_df.at[idx, 'Q_Min_Valid_Cond_4'] = cond_4_min
            result_df.at[idx, 'Q_Min_Valid_Cond_5'] = cond_5_min
            result_df.at[idx, 'Q_Min_Valid_Cond_6'] = cond_6_min
            
            # ===== 步驟三：決定最終篩選報價 Q_hat =====
            
            Q_hat_Bid = None
            Q_hat_Ask = None
            Q_hat_Mid = None
            Q_hat_Source = None
            
            # ----- 優先順序 1：使用 Q_Last_Valid -----
            # 條件：有雙邊報價 且 非異常值
            if has_two_sided_quote(Q_Last_Valid_Bid, Q_Last_Valid_Ask) and not is_outlier_last:
                Q_hat_Bid = float(Q_Last_Valid_Bid)
                Q_hat_Ask = float(Q_Last_Valid_Ask)
                Q_hat_Mid = float(Q_Last_Valid_Mid)
                Q_hat_Source = "Q_Last_Valid"
            
            # ----- 優先順序 2：使用 Q_Min_Valid -----
            # 條件：Q_Last_Valid 不可用，但 Q_Min_Valid 有雙邊報價 且 非異常值
            elif has_two_sided_quote(Q_Min_Valid_Bid, Q_Min_Valid_Ask) and not is_outlier_min:
                Q_hat_Bid = float(Q_Min_Valid_Bid)
                Q_hat_Ask = float(Q_Min_Valid_Ask)
                Q_hat_Mid = float(Q_Min_Valid_Mid)
                Q_hat_Source = "Q_Min_Valid"
            
            # ----- 優先順序 3：沿用前值 -----
            # 條件：上述皆不符合，使用前一時點的 Q_hat
            else:
                Q_hat_Bid = Q_hat_Bid_prev
                Q_hat_Ask = Q_hat_Ask_prev
                Q_hat_Mid = Q_hat_Mid_prev
                Q_hat_Source = "Replacement"
            
            # 寫入步驟三結果
            result_df.at[idx, 'Q_hat_Bid'] = Q_hat_Bid
            result_df.at[idx, 'Q_hat_Ask'] = Q_hat_Ask
            result_df.at[idx, 'Q_hat_Mid'] = Q_hat_Mid
            result_df.at[idx, 'Q_hat_Source'] = Q_hat_Source
            
            # [修正] 決定最終報告的 Gamma (Reported Gamma)
            # 邏輯：報告「被選中」的報價的 Gamma
            if Q_hat_Source == "Q_Last_Valid":
                final_gamma = gamma_last
            elif Q_hat_Source == "Q_Min_Valid":
                final_gamma = gamma_min
            else: # Replacement (即皆為 Outlier)
                # 當皆為 Outlier 時，PROD 似乎優先報告 Q_Min Gamma (如 Strike 27400 Put 案例)
                if is_valid_value(Q_Min_Valid_Bid) and is_valid_value(gamma_min):
                    final_gamma = gamma_min
                else:
                    final_gamma = gamma_last
            
            result_df.at[idx, 'Q_Last_Valid_Gamma'] = final_gamma
            
            # 更新前一時點狀態（供下一個時間點使用）
            Q_hat_Bid_prev = Q_hat_Bid
            Q_hat_Ask_prev = Q_hat_Ask
            Q_hat_Mid_prev = Q_hat_Mid
    
    return result_df


# ==============================================================================
# 主程式入口（測試用）
# ==============================================================================

def main(target_date=None):
    """
    測試 EMA 計算與異常值偵測
    
    【測試流程】
    1. 讀取步驟一產生的 CSV 檔案
    2. 執行步驟二與步驟三
    3. 輸出結果並列印統計
    """
    print("=" * 60)
    print("Step 0 步驟二與步驟三：異常值偵測 + 篩選後報價決定")
    print("=" * 60)
    print()
    
    # 取得設定
    from vix_utils import get_vix_config
    config = get_vix_config(target_date)
    final_date = config["target_date"]
    
    print(f"[Config] Target Date: {final_date}")
    
    # 讀取步驟一產生的 CSV
    # 注意：之前的步驟一輸出檔名含有日期
    near_csv = f"output/驗證{final_date}_Near_step1.csv"
    next_csv = f"output/驗證{final_date}_Next_step1.csv"
    
    print(f">>> 讀取步驟一結果...")
    near_df = pd.read_csv(near_csv)
    next_df = pd.read_csv(next_csv)
    
    print(f"    Near Term: {len(near_df)} 筆")
    print(f"    Next Term: {len(next_df)} 筆")
    
    # 執行步驟二與步驟三
    print(f"\n>>> 處理 Near Term...")
    near_with_ema = add_ema_and_outlier_detection(near_df, 'Near')
    
    print(f"\n>>> 處理 Next Term...")
    next_with_ema = add_ema_and_outlier_detection(next_df, 'Next')
    
    # 只輸出 PROD 格式結果（Call/Put 合併、c./p. 前綴）
    near_output = f"output/驗證{target_date}_NearPROD.csv"
    next_output = f"output/驗證{target_date}_NextPROD.csv"
    
    print(f"\n>>> 轉換並儲存 PROD 格式結果...")
    save_prod_format(near_with_ema, near_output, snapshot_sysid_col='Snapshot_SysID', date_val=final_date)
    save_prod_format(next_with_ema, next_output, snapshot_sysid_col='Snapshot_SysID', date_val=final_date)
    
    # 列印統計資訊
    print(f"\n" + "=" * 60)
    print("統計資訊")
    print("=" * 60)
    
    print(f"\n【Near Term】")
    print(f"  Q_Last_Valid 異常值: {near_with_ema['Q_Last_Valid_Is_Outlier'].sum()} / {len(near_with_ema)}")
    print(f"  Q_Min_Valid 異常值:  {near_with_ema['Q_Min_Valid_Is_Outlier'].sum()} / {len(near_with_ema)}")
    print(f"  Q_hat 來源分布:")
    print(near_with_ema['Q_hat_Source'].value_counts().to_string(name=False))
    
    print(f"\n【Next Term】")
    print(f"  Q_Last_Valid 異常值: {next_with_ema['Q_Last_Valid_Is_Outlier'].sum()} / {len(next_with_ema)}")
    print(f"  Q_Min_Valid 異常值:  {next_with_ema['Q_Min_Valid_Is_Outlier'].sum()} / {len(next_with_ema)}")
    print(f"  Q_hat 來源分布:")
    print(next_with_ema['Q_hat_Source'].value_counts().to_string(name=False))
    
    # 清理中間檔案 (Step 1 CSV)
    import os
    try:
        print(f"\n>>> 清理中間檔案...")
        if os.path.exists(near_csv):
            os.remove(near_csv)
            print(f"  已刪除: {near_csv}")
        if os.path.exists(next_csv):
            os.remove(next_csv)
            print(f"  已刪除: {next_csv}")
    except Exception as e:
        print(f"  清理失敗: {e}")


# ==============================================================================
# PROD 格式輸出轉換（只調整輸出格式，不動計算邏輯）
# ==============================================================================

def convert_outlier_to_prod_format(is_outlier, cond_1, cond_2, cond_3, cond_4, cond_5=False, cond_6=False):
    """
    將異常值標記轉換為 PROD 格式
    
    【轉換規則】
    - 無資料或無法判定 → "-"
    - 是異常值 (True) → "V" (Violation)
    - 非異常值 (False) → 輸出符合的條件編號，如 "1", "2", "1,2" 等
    - 例外情況 2（第一筆資料/Q_hat_Mid_prev 為 null）→ "5"
    - 例外情況 3（EMA 為 null）→ "6"
    
    Args:
        is_outlier: 是否為異常值 (True/False/None)
        cond_1~4: 各條件是否通過
        cond_5: 例外情況 2（第一筆資料）
        cond_6: 例外情況 3（EMA 為 null）
        
    Returns:
        str: PROD 格式的異常值標記
    """
    # 無資料情況
    if is_outlier is None or pd.isna(is_outlier):
        return "-"
    
    # 異常值
    if is_outlier == True:
        return "V"
    
    # 非異常值：輸出符合的條件編號
    passed_conds = []
    if cond_1:
        passed_conds.append("1")
    if cond_2:
        passed_conds.append("2")
    if cond_3:
        passed_conds.append("3")
    if cond_4:
        passed_conds.append("4")
    if cond_5:
        passed_conds.append("5")
    if cond_6:
        passed_conds.append("6")
    
    if passed_conds:
        return ",".join(passed_conds)
    else:
        # 非異常值但沒有任何條件通過（理論上不應該發生）
        return "-"


def convert_to_prod_format(df, snapshot_sysid_col='Snapshot_SysID'):
    """
    將計算結果轉換為 PROD 格式
    
    【格式變更】
    - 一列 = (Time, Strike)，Call/Put 合併
    - 欄位使用 c./p. 前綴
    - Outlier 標記改為字串格式
    
    【注意】此函式只處理輸出格式，不動任何計算邏輯
    
    Args:
        df: 計算結果 DataFrame（包含 CP 欄位區分 Call/Put）
        snapshot_sysid_col: snapshot_sysID 欄位名稱
        
    Returns:
        DataFrame: PROD 格式的輸出
    """
    # 分離 Call 和 Put
    call_df = df[df['CP'] == 'Call'].copy()
    put_df = df[df['CP'] == 'Put'].copy()
    
    # 轉換 Outlier 標記（Call）
    call_df['c.last_outlier'] = call_df.apply(
        lambda row: convert_outlier_to_prod_format(
            row.get('Q_Last_Valid_Is_Outlier'),
            row.get('Q_Last_Valid_Cond_1'),
            row.get('Q_Last_Valid_Cond_2'),
            row.get('Q_Last_Valid_Cond_3'),
            row.get('Q_Last_Valid_Cond_4'),
            row.get('Q_Last_Valid_Cond_5'),
            row.get('Q_Last_Valid_Cond_6')
        ), axis=1
    )
    call_df['c.min_outlier'] = call_df.apply(
        lambda row: convert_outlier_to_prod_format(
            row.get('Q_Min_Valid_Is_Outlier'),
            row.get('Q_Min_Valid_Cond_1'),
            row.get('Q_Min_Valid_Cond_2'),
            row.get('Q_Min_Valid_Cond_3'),
            row.get('Q_Min_Valid_Cond_4'),
            row.get('Q_Min_Valid_Cond_5'),
            row.get('Q_Min_Valid_Cond_6')
        ), axis=1
    )
    
    # 轉換 Outlier 標記（Put）
    put_df['p.last_outlier'] = put_df.apply(
        lambda row: convert_outlier_to_prod_format(
            row.get('Q_Last_Valid_Is_Outlier'),
            row.get('Q_Last_Valid_Cond_1'),
            row.get('Q_Last_Valid_Cond_2'),
            row.get('Q_Last_Valid_Cond_3'),
            row.get('Q_Last_Valid_Cond_4'),
            row.get('Q_Last_Valid_Cond_5'),
            row.get('Q_Last_Valid_Cond_6')
        ), axis=1
    )
    put_df['p.min_outlier'] = put_df.apply(
        lambda row: convert_outlier_to_prod_format(
            row.get('Q_Min_Valid_Is_Outlier'),
            row.get('Q_Min_Valid_Cond_1'),
            row.get('Q_Min_Valid_Cond_2'),
            row.get('Q_Min_Valid_Cond_3'),
            row.get('Q_Min_Valid_Cond_4'),
            row.get('Q_Min_Valid_Cond_5'),
            row.get('Q_Min_Valid_Cond_6')
        ), axis=1
    )
    
    # Call 欄位重命名
    call_rename = {
        'EMA': 'c.ema',
        'Q_Last_Valid_Gamma': 'c.gamma',
        'Q_Last_Valid_Bid': 'c.last_bid',
        'Q_Last_Valid_Ask': 'c.last_ask',
        'Q_last_SysID': 'c.last_sysID',
        'Q_Min_Valid_Bid': 'c.min_bid',
        'Q_Min_Valid_Ask': 'c.min_ask',
        'Q_min_SysID': 'c.min_sysID',
        'Q_hat_Bid': 'c.bid',
        'Q_hat_Ask': 'c.ask',
        'Q_hat_Source': 'c.source',
    }
    
    # Put 欄位重命名
    put_rename = {
        'EMA': 'p.ema',
        'Q_Last_Valid_Gamma': 'p.gamma',
        'Q_Last_Valid_Bid': 'p.last_bid',
        'Q_Last_Valid_Ask': 'p.last_ask',
        'Q_last_SysID': 'p.last_sysID',
        'Q_Min_Valid_Bid': 'p.min_bid',
        'Q_Min_Valid_Ask': 'p.min_ask',
        'Q_min_SysID': 'p.min_sysID',
        'Q_hat_Bid': 'p.bid',
        'Q_hat_Ask': 'p.ask',
        'Q_hat_Source': 'p.source',
    }
    
    # 選擇需要的欄位（Call）
    call_cols = ['Time', 'Strike', snapshot_sysid_col, 
                 'c.ema', 'c.gamma', 
                 'c.last_bid', 'c.last_ask', 'c.last_sysID', 'c.last_outlier',
                 'c.min_bid', 'c.min_ask', 'c.min_sysID', 'c.min_outlier',
                 'c.bid', 'c.ask', 'c.source']
    
    # 選擇需要的欄位（Put）
    put_cols = ['Time', 'Strike', 
                'p.ema', 'p.gamma',
                'p.last_bid', 'p.last_ask', 'p.last_sysID', 'p.last_outlier',
                'p.min_bid', 'p.min_ask', 'p.min_sysID', 'p.min_outlier',
                'p.bid', 'p.ask', 'p.source']
    
    # 重命名欄位
    call_df = call_df.rename(columns=call_rename)
    put_df = put_df.rename(columns=put_rename)
    
    # 處理可能不存在的欄位
    for col in call_cols:
        if col not in call_df.columns:
            call_df[col] = np.nan
    for col in put_cols:
        if col not in put_df.columns:
            put_df[col] = np.nan
    
    call_df = call_df[call_cols]
    put_df = put_df[put_cols]
    
    # 重命名共用欄位
    call_df = call_df.rename(columns={snapshot_sysid_col: 'snapshot_sysID'})
    call_df = call_df.rename(columns={'Time': 'time', 'Strike': 'strike'})
    put_df = put_df.rename(columns={'Time': 'time', 'Strike': 'strike'})
    
    # 合併 Call 和 Put
    output_df = pd.merge(
        call_df, 
        put_df, 
        on=['time', 'strike'], 
        how='outer'
    )
    
    # 【修正】Bid=NaN 時（merge 後該側不存在），gamma 填入 GAMMA_0 (1.2)
    # PROD 對無資料的一側仍輸出 gamma=1.2（bid=0 或 bid=NaN → GAMMA_0）
    output_df['c.gamma'] = output_df['c.gamma'].fillna(GAMMA_0)
    output_df['p.gamma'] = output_df['p.gamma'].fillna(GAMMA_0)
    
    # 新增 date 欄位
    # 我們假設 df 裡面的 Time 是 HHMMSS，而日期是外部傳入的 target_date
    # 但這裡 convert_to_prod_format 沒收到 target_date 參數
    # 我們可以嘗試從全域變數或參數傳遞取得，或者先留空
    # 更好的方式是修改 convert_to_prod_format 的簽名接受 date 參數
    # 但為了最小改動，我們看能不能從 sys.argv 拿，或者依賴 caller 處理
    # 這裡我們暫時放空字串，然後在 save_prod_format 補上
    # 或者我們可以解析 time 欄位如果它包含日期的話？目前的 time 只有 HHMMSS
    
    # 既然 User 希望在第一欄新增資料日期，我們修改 convert_to_prod_format 簽名
    # 但為了相容性，我們先回傳 output_df，在 save_prod_format 處理 date 欄位
    
    # 排序
    output_df = output_df.sort_values(['time', 'strike']).reset_index(drop=True)
    
    # 定義 PROD 欄位順序 (只包含我們有的)
    # 參考: ['date', 'time', 'strike', 'c.bid', 'c.ask', 'p.bid', 'p.ask', 
    #        'c.source', 'p.source', 'c.sysID', 'p.sysID', 
    #        'c.last_bid', 'c.last_ask', 'c.last_sysID', 'c.last_outlier', 
    #        'p.last_bid', 'p.last_ask', 'p.last_sysID', 'p.last_outlier', 
    #        'c.min_bid', 'c.min_ask', 'c.min_sysID', 'c.min_outlier', 
    #        'p.min_bid', 'p.min_ask', 'p.min_sysID', 'p.min_outlier', 
    #        'c.ema', 'p.ema', 'c.gamma', 'p.gamma', 'snapshot_sysID']
    
    prod_order = [
         'time', 'strike',
         'c.bid', 'c.ask', 
         'p.bid', 'p.ask',
         'c.source', 'p.source', # 對應 c.type, p.type
         # c.sysID, p.sysID (missing)
         'c.last_bid', 'c.last_ask', 'c.last_sysID', 'c.last_outlier',
         'p.last_bid', 'p.last_ask', 'p.last_sysID', 'p.last_outlier',
         'c.min_bid', 'c.min_ask', 'c.min_sysID', 'c.min_outlier',
         'p.min_bid', 'p.min_ask', 'p.min_sysID', 'p.min_outlier',
         'c.ema', 'p.ema',
         'c.gamma', 'p.gamma',
         'snapshot_sysID'
    ]
    
    # 過濾出存在的欄位
    final_cols = [c for c in prod_order if c in output_df.columns]
    
    return output_df[final_cols]


def save_prod_format(df, output_path, snapshot_sysid_col='Snapshot_SysID', date_val=None):
    """
    將計算結果以 PROD 格式儲存
    
    Args:
        df: 計算結果 DataFrame
        output_path: 輸出路徑
        snapshot_sysid_col: snapshot_sysID 欄位名稱
        date_val: 日期欄位的值 (YYYYMMDD)
    """
    prod_df = convert_to_prod_format(df, snapshot_sysid_col)
    
    # 將所有數值欄位的 null/NaN 填為 0（Q_hat、Q_Last、Q_Min、EMA）
    # 注意：計算過程中空值可能以字串 "null" 或 Python NaN 兩種形式存在
    fill_zero_cols = [
        'c.bid', 'c.ask', 'p.bid', 'p.ask',           # Q_hat
        'c.last_bid', 'c.last_ask',                     # Q_Last_Valid
        'p.last_bid', 'p.last_ask',                     # Q_Last_Valid
        'c.min_bid', 'c.min_ask',                       # Q_Min_Valid
        'p.min_bid', 'p.min_ask',                       # Q_Min_Valid
        'c.ema', 'p.ema',                               # EMA
    ]
    for col in fill_zero_cols:
        if col in prod_df.columns:
            prod_df[col] = prod_df[col].replace({'null': 0, '': 0}).fillna(0)
    
    # 如果有提供日期，加入 date 欄位並放在第一欄
    if date_val:
        prod_df.insert(0, 'date', date_val)
        
    prod_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"PROD 格式已儲存: {output_path}")
    return prod_df


if __name__ == "__main__":
    import sys
    # 簡單支援從命令列傳入第一個參數作為日期 (如果不是 --date 的話)
    # 但因為 get_vix_config 會處理 --date，這裡只要負責把參數傳給 main 即可
    # 如果使用者用 python script.py 20251231
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        main(sys.argv[1])
    else:
        main()
