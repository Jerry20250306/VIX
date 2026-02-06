"""
Step 0 步驟二：異常值偵測 (Outlier Detection via EMA)
依據附錄 3 實作 EMA 計算與異常值判定
"""
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# EMA 計算參數
ALPHA = 0.95  # EMA 計算參數（高權重給當前價差）
GAMMA_0 = 1.2  # Bid = 0 時使用
GAMMA_1 = 2.0  # Bid > 0 且 Mid <= γ1 時使用
GAMMA_2 = 2.5  # Bid > 0 且 Mid > γ1 時使用
S_MAX = 0.95   # 最大價差參數（與 Alpha 相同）

def calculate_ema_for_series(time_series_df):
    """
    為單個序列（Strike + CP）計算所有時點的 EMA
    
    Args:
        time_series_df: 該序列的所有時間點資料，需包含以下欄位：
            - Time (字串，例如 '084500')
            - Q_Min_Valid_Spread (有效時為數值，無效時為 "null")
            - Q_Min_Valid_Bid, Q_Min_Valid_Ask, Q_Min_Valid_Mid
            
    Returns:
        time_series_df: 新增 EMA 和 EMA_Process 欄位的 DataFrame
    """
    # 按時間排序
    df = time_series_df.sort_values('Time').copy()
    
    # 初始化 EMA 欄位
    df['EMA'] = None
    df['EMA_Process'] = None  # 記錄使用的公式
    
    prev_ema = None
    
    for idx, row in df.iterrows():
        spread = row['Q_Min_Valid_Spread']
        
        # 檢查是否為 null（字串 "null" 或實際的 null/NaN）
        is_null = (spread == "null" or pd.isna(spread))
        
        if prev_ema is None:
            # 情況1：第一次計算
            if is_null:
                ema = "null"  # 第一個時間區間無有效報價
                process = "初始值：Q_Min_Valid為null → EMA=null"
            else:
                ema = float(spread)  # 直接使用第一個有效價差
                process = f"初始值：EMA_0 = Q_Min_Valid_Spread = {spread}"
        else:
            # 有前一時點的 EMA
            if prev_ema == "null":
                # 前一時點 EMA 為 null
                if is_null:
                    ema = "null"
                    process = "EMA_{t-1}為null，Q_Min_Valid為null → EMA_t=null"
                else:
                    ema = float(spread)
                    process = f"EMA_{{t-1}}為null → EMA_t = Q_Min_Valid_Spread = {spread}"
            else:
                # 前一時點 EMA 有值
                if is_null:
                    # 情況2：當前無有效報價，EMA 保持不變
                    ema = prev_ema
                    process = f"Q_Min_Valid為null → EMA_t = EMA_{{t-1}} = {prev_ema:.6f}"
                else:
                    # 情況3：正常計算
                    ema = (1 - ALPHA) * prev_ema + ALPHA * float(spread)
                    process = f"正常公式：EMA_t = 0.05×{prev_ema:.6f} + 0.95×{spread} = {ema:.6f}"
        
        df.at[idx, 'EMA'] = ema
        df.at[idx, 'EMA_Process'] = process
        prev_ema = ema
    
    return df


def determine_gamma(prev_filtered_bid, prev_filtered_mid):
    """
    根據前一時點篩選後的報價，決定 γ 參數
    
    Args:
        prev_filtered_bid: 前一時點篩選後的 Bid（步驟三結果）
        prev_filtered_mid: 前一時點篩選後的 Mid（步驟三結果）
        
    Returns:
        (gamma, process): γ 值和判斷過程說明
    """
    # 檢查是否為 null
    if prev_filtered_bid is None or pd.isna(prev_filtered_bid) or prev_filtered_bid == "null" or prev_filtered_bid == "":
        return GAMMA_0, f"Q(t-1)_Bid為null → γ = γ₀ = {GAMMA_0}"
    
    bid_val = float(prev_filtered_bid)
    
    if bid_val == 0:
        return GAMMA_0, f"Q(t-1)_Bid = 0 → γ = γ₀ = {GAMMA_0}"
    
    # Bid > 0，需要檢查 Mid
    if prev_filtered_mid is None or pd.isna(prev_filtered_mid) or prev_filtered_mid == "null" or prev_filtered_mid == "":
        # Mid 為 null 時，預設使用 γ₀
        return GAMMA_0, f"Q(t-1)_Bid = {bid_val} > 0，但 Mid 為 null → γ = γ₀ = {GAMMA_0}"
    
    mid_val = float(prev_filtered_mid)
    
    if mid_val <= GAMMA_1:
        return GAMMA_1, f"Q(t-1)_Bid = {bid_val} > 0 且 Mid = {mid_val} ≤ {GAMMA_1} → γ = γ₁ = {GAMMA_1}"
    else:
        return GAMMA_2, f"Q(t-1)_Bid = {bid_val} > 0 且 Mid = {mid_val} > {GAMMA_1} → γ = γ₂ = {GAMMA_2}"


def check_outlier(spread, bid, mid, ema_t, ema_t_minus_1, gamma):
    """
    檢查報價是否為異常值
    
    報價符合任一條件即為「非異常值」：
    - Condition i:   Spread <= S_max
    - Condition ii:  Spread <= EMA_t × γ
    - Condition iii: Spread <= EMA_{t-1} × γ
    - Condition iv:  Bid > 0 且 Mid <= γ
    
    Args:
        spread: 當前價差
        bid: 當前買價
        mid: 當前中價
        ema_t: 當前 EMA
        ema_t_minus_1: 前一時點 EMA
        gamma: γ 參數
        
    Returns:
        (is_outlier: bool, reason: str, cond_i: bool, cond_ii: bool, cond_iii: bool, cond_iv: bool)
        is_outlier = True 表示為異常值
        is_outlier = False 表示為非異常值
        cond_X = True 表示該條件通過（非異常值）
    """
    # 初始化所有條件為 False
    cond_i = False
    cond_ii = False
    cond_iii = False
    cond_iv = False
    
    # 特殊情況：null 視為非異常值
    if spread == "null" or pd.isna(spread) or spread == "":
        return False, "null視為非異常值", False, False, False, False
    
    spread_val = float(spread)
    
    # Condition i: Spread <= S_max
    if spread_val <= S_MAX:
        cond_i = True
        return False, f"Condition i: Spread({spread_val}) <= S_max({S_MAX})", cond_i, cond_ii, cond_iii, cond_iv
    
    # Condition ii: Spread <= EMA_t × γ
    # EMA 可能是 "null" 字串、空白或數值
    if ema_t is not None and ema_t != "null" and ema_t != "" and not pd.isna(ema_t):
        ema_t_val = float(ema_t)
        threshold_ii = ema_t_val * gamma
        if spread_val <= threshold_ii:
            cond_ii = True
            return False, f"Condition ii: Spread({spread_val}) <= EMA_t({ema_t_val:.4f}) × γ({gamma}) = {threshold_ii:.4f}", cond_i, cond_ii, cond_iii, cond_iv
    
    # Condition iii: Spread <= EMA_{t-1} × γ
    if ema_t_minus_1 is not None and ema_t_minus_1 != "null" and ema_t_minus_1 != "" and not pd.isna(ema_t_minus_1):
        ema_t_minus_1_val = float(ema_t_minus_1)
        threshold_iii = ema_t_minus_1_val * gamma
        if spread_val <= threshold_iii:
            cond_iii = True
            return False, f"Condition iii: Spread({spread_val}) <= EMA_t-1({ema_t_minus_1_val:.4f}) × γ({gamma}) = {threshold_iii:.4f}", cond_i, cond_ii, cond_iii, cond_iv
    
    # Condition iv: Bid > 0 且 Mid <= γ
    if bid != "null" and bid != "" and not pd.isna(bid):
        bid_val = float(bid)
        if mid != "null" and mid != "" and not pd.isna(mid):
            mid_val = float(mid)
            if bid_val > 0 and mid_val <= gamma:
                cond_iv = True
                return False, f"Condition iv: Bid({bid_val}) > 0 且 Mid({mid_val}) <= γ({gamma})", cond_i, cond_ii, cond_iii, cond_iv
    
    # 不符合任一條件 → 異常值
    return True, "不符合任一非異常值條件", cond_i, cond_ii, cond_iii, cond_iv


def add_ema_and_outlier_detection(df, term_name):
    """
    為整個 Term 的所有序列計算 EMA 並判定異常值
    
    Args:
        df: 包含所有時間點的資料，需先經過步驟一產生 Q_Min_Valid_* 欄位
        term_name: 'Near' or 'Next'
        
    Returns:
        df: 新增 EMA, Gamma, Q_Last_Outlier, Q_Min_Outlier 等欄位
    """
    # 為每個序列（Strike + CP）分別計算 EMA
    all_series = []
    
    for (strike, cp), group in df.groupby(['Strike', 'CP'], sort=False):
        print(f"  處理序列: Strike={strike}, CP={cp}")
        series_df = calculate_ema_for_series(group)
        all_series.append(series_df)
    
    # 合併所有序列
    result_df = pd.concat(all_series, ignore_index=True)
    
    # 初始化新欄位
    result_df['Gamma'] = None
    result_df['Gamma_Process'] = None  # 記錄 gamma 判斷過程
    result_df['Q_last_Is_Outlier'] = None
    result_df['Q_last_Outlier_Reason'] = None
    result_df['Q_last_Cond_i'] = None
    result_df['Q_last_Cond_ii'] = None
    result_df['Q_last_Cond_iii'] = None
    result_df['Q_last_Cond_iv'] = None
    result_df['Q_min_Is_Outlier'] = None
    result_df['Q_min_Outlier_Reason'] = None
    result_df['Q_min_Cond_i'] = None
    result_df['Q_min_Cond_ii'] = None
    result_df['Q_min_Cond_iii'] = None
    result_df['Q_min_Cond_iv'] = None
    
    # 按時間排序（暫時不考慮前一時點篩選結果，先用 Q_Min_Valid）
    result_df = result_df.sort_values(['Strike', 'CP', 'Time']).reset_index(drop=True)
    
    # 為每個序列判定異常值
    for (strike, cp), group_indices in result_df.groupby(['Strike', 'CP'], sort=False).groups.items():
        prev_filtered_bid = None
        prev_filtered_mid = None
        prev_ema = None
        
        for i, idx in enumerate(group_indices):
            row = result_df.loc[idx]
            
            # 決定 gamma（基於前一時點的篩選結果）
            # 注意：這裡暫時使用 Q_Min_Valid，在步驟三會更新為實際篩選結果
            gamma, gamma_process = determine_gamma(prev_filtered_bid, prev_filtered_mid)
            result_df.at[idx, 'Gamma'] = gamma
            result_df.at[idx, 'Gamma_Process'] = gamma_process
            
            current_ema = row['EMA']
            
            # 判定 Q_last 是否為異常值
            q_last_spread = row['Q_Last_Valid_Spread']
            q_last_bid = row['Q_Last_Valid_Bid']
            q_last_mid = row['Q_Last_Valid_Mid']
            
            is_outlier_last, reason_last, cond_i_last, cond_ii_last, cond_iii_last, cond_iv_last = check_outlier(
                q_last_spread, q_last_bid, q_last_mid,
                current_ema, prev_ema, gamma
            )
            result_df.at[idx, 'Q_last_Is_Outlier'] = is_outlier_last
            result_df.at[idx, 'Q_last_Outlier_Reason'] = reason_last
            result_df.at[idx, 'Q_last_Cond_i'] = cond_i_last
            result_df.at[idx, 'Q_last_Cond_ii'] = cond_ii_last
            result_df.at[idx, 'Q_last_Cond_iii'] = cond_iii_last
            result_df.at[idx, 'Q_last_Cond_iv'] = cond_iv_last
            
            # 判定 Q_min 是否為異常值
            q_min_spread = row['Q_Min_Valid_Spread']
            q_min_bid = row['Q_Min_Valid_Bid']
            q_min_mid = row['Q_Min_Valid_Mid']
            
            is_outlier_min, reason_min, cond_i_min, cond_ii_min, cond_iii_min, cond_iv_min = check_outlier(
                q_min_spread, q_min_bid, q_min_mid,
                current_ema, prev_ema, gamma
            )
            result_df.at[idx, 'Q_min_Is_Outlier'] = is_outlier_min
            result_df.at[idx, 'Q_min_Outlier_Reason'] = reason_min
            result_df.at[idx, 'Q_min_Cond_i'] = cond_i_min
            result_df.at[idx, 'Q_min_Cond_ii'] = cond_ii_min
            result_df.at[idx, 'Q_min_Cond_iii'] = cond_iii_min
            result_df.at[idx, 'Q_min_Cond_iv'] = cond_iv_min
            
            # 更新前一時點的資訊（暫時用 Q_Min_Valid，步驟三會更新）
            prev_filtered_bid = q_min_bid
            prev_filtered_mid = q_min_mid
            prev_ema = current_ema
    
    return result_df


def main():
    """測試 EMA 計算與異常值偵測"""
    print("=== Step 0 步驟二：異常值偵測 (EMA 計算) ===\n")
    
    # 讀取步驟一產生的 CSV（前5個時間點）
    near_csv = "step0_1_valid_quotes_Near_測試前5個.csv"
    next_csv = "step0_1_valid_quotes_Next_測試前5個.csv"
    
    print(f">>> 讀取步驟一結果...")
    near_df = pd.read_csv(near_csv)
    next_df = pd.read_csv(next_csv)
    
    print(f"  Near Term: {len(near_df)} 筆")
    print(f"  Next Term: {len(next_df)} 筆")
    
    # 為 Near Term 計算 EMA 與異常值
    print(f"\n>>> 處理 Near Term EMA 與異常值偵測...")
    near_with_ema = add_ema_and_outlier_detection(near_df, 'Near')
    
    # 為 Next Term 計算 EMA 與異常值
    print(f"\n>>> 處理 Next Term EMA 與異常值偵測...")
    next_with_ema = add_ema_and_outlier_detection(next_df, 'Next')
    
    # 儲存結果
    near_output = "step0_2_ema_outlier_Near_測試前5個.csv"
    next_output = "step0_2_ema_outlier_Next_測試前5個.csv"
    
    near_with_ema.to_csv(near_output, index=False, encoding='utf-8-sig')
    next_with_ema.to_csv(next_output, index=False, encoding='utf-8-sig')
    
    print(f"\n>>> 結果已儲存:")
    print(f"  {near_output}")
    print(f"  {next_output}")
    
    # 列印統計
    print(f"\n=== Near Term 異常值統計 ===")
    print(f"Q_last 異常值: {near_with_ema['Q_last_Is_Outlier'].sum()} / {len(near_with_ema)}")
    print(f"Q_min 異常值: {near_with_ema['Q_min_Is_Outlier'].sum()} / {len(near_with_ema)}")
    
    print(f"\n=== Next Term 異常值統計 ===")
    print(f"Q_last 異常值: {next_with_ema['Q_last_Is_Outlier'].sum()} / {len(next_with_ema)}")
    print(f"Q_min 異常值: {next_with_ema['Q_min_Is_Outlier'].sum()} / {len(next_with_ema)}")


if __name__ == "__main__":
    main()
