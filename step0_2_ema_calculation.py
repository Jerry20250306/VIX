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
  - Lambda (λ):   最大允許價差門檻（0.5 點）

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
LAMBDA = 0.5    # 最大允許價差（點數）：Spread < 0.5 點一律視為非異常值


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
    
    # 初始化 EMA 相關欄位
    df['EMA'] = None           # EMA 數值
    df['EMA_Process'] = None   # EMA 計算過程說明（供除錯用）
    
    # 追蹤前一時點的 EMA（用於遞迴計算）
    prev_ema = None
    
    # 逐筆迭代計算 EMA
    for idx, row in df.iterrows():
        # 取得當前時間點的 Q_Min_Valid 價差
        spread = row['Q_Min_Valid_Spread']
        
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
        
        # 寫入計算結果
        df.at[idx, 'EMA'] = ema
        df.at[idx, 'EMA_Process'] = process
        
        # 更新 prev_ema 供下一次迭代使用
        prev_ema = ema
    
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
    if mid_val <= prev_mid_val:
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
        tuple: (is_outlier, reason, cond_1, cond_2, cond_3, cond_4)
            - is_outlier: True=異常值, False=非異常值
            - reason: 判定原因說明
            - cond_1~4: 各條件是否通過
    """
    # 初始化所有條件狀態為 False
    cond_1 = False
    cond_2 = False
    cond_3 = False
    cond_4 = False
    
    # ===== 例外情況 1：報價本身為 null =====
    if not is_valid_value(spread):
        return False, "報價為 null → 視為非異常值", False, False, False, False
    
    # ===== 例外情況 2：Q_hat_Mid_t-1 為 null（第一筆資料）=====
    if not is_valid_value(Q_hat_Mid_t_minus_1):
        return False, "Q_hat_Mid_t-1 為 null（第一筆資料）→ 視為非異常值", False, False, False, False
    
    # ===== 例外情況 3：EMA_t-1 為 null =====
    # 依據 Spec：若前一期的 EMA 為 null（例如第一筆資料或連續無報價），則直接視為非異常值
    # 注意：這裡 ema_t 實際上是計算當期時使用的 EMA，但在第一筆資料時 EMA 會是 null
    # 因為 EMA 的計算邏輯是：先用 prev_ema 算 Gamma/Outlier，再更新 EMA
    # 所以當 ema_t 為 null 時，代表前一期沒有有效 EMA，等同於 EMA_t-1 為 null
    if not is_valid_value(ema_t):
        return False, "EMA_t-1 為 null → 視為非異常值", False, False, False, False
    
    # 轉換為數值進行比較
    spread_val = float(spread)
    prev_mid_val = float(Q_hat_Mid_t_minus_1)
    
    # ===== Condition 1：Spread <= γ × EMA_t =====
    if is_valid_value(ema_t):
        ema_t_val = float(ema_t)
        threshold_1 = gamma * ema_t_val
        if spread_val <= threshold_1:
            cond_1 = True
            return False, f"Condition 1：Spread({spread_val}) <= γ({gamma}) × EMA_t({ema_t_val:.4f}) = {threshold_1:.4f}", cond_1, cond_2, cond_3, cond_4
    
    # ===== Condition 2：Spread < λ =====
    if spread_val < LAMBDA:
        cond_2 = True
        return False, f"Condition 2：Spread({spread_val}) < λ({LAMBDA})", cond_1, cond_2, cond_3, cond_4
    
    # ===== Condition 3 & 4 需要 Bid 和 Ask =====
    if is_valid_value(bid):
        bid_val = float(bid)
        
        # ----- Condition 3：Bid_t > Q_hat_Mid_t-1（買價突破上一期中價）-----
        if bid_val > prev_mid_val:
            cond_3 = True
            return False, f"Condition 3：Bid({bid_val}) > Q_hat_Mid_t-1({prev_mid_val})", cond_1, cond_2, cond_3, cond_4
        
        # ----- Condition 4：Ask_t < Q_hat_Mid_t-1 且 Bid_t > 0（賣價跌破上一期中價）-----
        if is_valid_value(ask):
            ask_val = float(ask)
            if ask_val < prev_mid_val and bid_val > 0:
                cond_4 = True
                return False, f"Condition 4：Ask({ask_val}) < Q_hat_Mid_t-1({prev_mid_val}) 且 Bid({bid_val}) > 0", cond_1, cond_2, cond_3, cond_4
    
    # ===== 不符合任一條件 → 判定為異常值 =====
    return True, "不符合任一非異常值條件 → 判定為異常值", cond_1, cond_2, cond_3, cond_4


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
    
    # Q_Min_Valid 異常值判定結果
    result_df['Q_Min_Valid_Is_Outlier'] = None       # 是否為異常值
    result_df['Q_Min_Valid_Outlier_Reason'] = None   # 判定原因
    result_df['Q_Min_Valid_Cond_1'] = None           # Condition 1 是否通過
    result_df['Q_Min_Valid_Cond_2'] = None           # Condition 2 是否通過
    result_df['Q_Min_Valid_Cond_3'] = None           # Condition 3 是否通過
    result_df['Q_Min_Valid_Cond_4'] = None           # Condition 4 是否通過
    
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
            is_outlier_last, reason_last, cond_1_last, cond_2_last, cond_3_last, cond_4_last = check_outlier(
                Q_Last_Valid_Spread, Q_Last_Valid_Bid, Q_Last_Valid_Ask,
                current_ema, gamma_last, Q_hat_Mid_prev
            )
            result_df.at[idx, 'Q_Last_Valid_Is_Outlier'] = is_outlier_last
            result_df.at[idx, 'Q_Last_Valid_Outlier_Reason'] = reason_last
            result_df.at[idx, 'Q_Last_Valid_Cond_1'] = cond_1_last
            result_df.at[idx, 'Q_Last_Valid_Cond_2'] = cond_2_last
            result_df.at[idx, 'Q_Last_Valid_Cond_3'] = cond_3_last
            result_df.at[idx, 'Q_Last_Valid_Cond_4'] = cond_4_last
            
            # 判定 Q_Min_Valid 是否為異常值
            is_outlier_min, reason_min, cond_1_min, cond_2_min, cond_3_min, cond_4_min = check_outlier(
                Q_Min_Valid_Spread, Q_Min_Valid_Bid, Q_Min_Valid_Ask,
                current_ema, gamma_min, Q_hat_Mid_prev
            )
            result_df.at[idx, 'Q_Min_Valid_Is_Outlier'] = is_outlier_min
            result_df.at[idx, 'Q_Min_Valid_Outlier_Reason'] = reason_min
            result_df.at[idx, 'Q_Min_Valid_Cond_1'] = cond_1_min
            result_df.at[idx, 'Q_Min_Valid_Cond_2'] = cond_2_min
            result_df.at[idx, 'Q_Min_Valid_Cond_3'] = cond_3_min
            result_df.at[idx, 'Q_Min_Valid_Cond_4'] = cond_4_min
            
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

def main():
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
    
    # 讀取步驟一產生的 CSV（測試前30個時間點）
    near_csv = "step0_1_valid_quotes_Near_測試前30個.csv"
    next_csv = "step0_1_valid_quotes_Next_測試前30個.csv"
    
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
    
    # 儲存結果
    near_output = "step0_full_output_Near_測試前30個.csv"
    next_output = "step0_full_output_Next_測試前30個.csv"
    
    near_with_ema.to_csv(near_output, index=False, encoding='utf-8-sig')
    next_with_ema.to_csv(next_output, index=False, encoding='utf-8-sig')
    
    print(f"\n>>> 結果已儲存:")
    print(f"    {near_output}")
    print(f"    {next_output}")
    
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


if __name__ == "__main__":
    main()
