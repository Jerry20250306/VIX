"""
測試腳本：執行 Step 0 前 10 個時間區間，並與官方 PROD 資料比對
================================================================================

【測試目的】
1. 執行步驟一（有效報價獲取）和步驟二、三（EMA、異常值判定、篩選後報價）
2. 輸出所有計算過程參數和條件判定結果
3. 將 Q_hat_Bid/Ask 與官方 PROD 檔案的 snapshot_call/put_bid/ask 比對
"""

import pandas as pd
import numpy as np
import sys
import os

# 載入本地模組
sys.path.insert(0, os.path.dirname(__file__))
from step0_valid_quotes import check_valid_quote
from step0_2_ema_calculation import (
    calculate_ema_for_series,
    determine_gamma,
    check_outlier,
    add_ema_and_outlier_detection,
    is_valid_value,
    has_two_sided_quote
)


def load_prod_data(file_path, num_times=10):
    """
    載入官方 PROD 資料（前 N 個時間區間）
    
    PROD 檔案結構：
    - 第一行：時間開頭行（只有 date 和 sysID）
    - 之後每 110 行為一個時間區間的資料
    
    重要欄位：
    - time: 時間點（如 084515）
    - strike: 履約價
    - snapshot_call_bid, snapshot_call_ask: Call 的篩選後報價
    - snapshot_put_bid, snapshot_put_ask: Put 的篩選後報價
    """
    # 讀取 TSV
    df = pd.read_csv(file_path, sep='\t', dtype=str)
    
    # 過濾掉時間開頭行（沒有 strike 的行）
    df = df[df['strike'].notna() & (df['strike'] != '')].copy()
    
    # 取得唯一的時間點
    times = df['time'].unique()[:num_times]
    print(f"  載入時間點: {list(times)}")
    
    # 篩選前 N 個時間區間
    df = df[df['time'].isin(times)].copy()
    
    return df, times


def compare_results(calculated_df, prod_df, term_name, cp):
    """
    比對計算結果與官方 PROD 資料
    
    Args:
        calculated_df: 我們計算的結果（Q_hat_Bid, Q_hat_Ask）
        prod_df: 官方 PROD 資料
        term_name: 'Near' 或 'Next'
        cp: 'C'（Call）或 'P'（Put）
    
    Returns:
        comparison_df: 比對結果 DataFrame
    
    注意：PROD 檔案中的 c.bid/c.ask 是 Call 的篩選後報價，p.bid/p.ask 是 Put 的篩選後報價
    """
    # 根據 CP 決定比對欄位
    if cp == 'C':
        prod_bid_col = 'c.bid'
        prod_ask_col = 'c.ask'
    else:
        prod_bid_col = 'p.bid'
        prod_ask_col = 'p.ask'
    
    # 確保欄位存在並轉換為數值
    prod_df = prod_df.copy()
    prod_df[prod_bid_col] = pd.to_numeric(prod_df[prod_bid_col], errors='coerce')
    prod_df[prod_ask_col] = pd.to_numeric(prod_df[prod_ask_col], errors='coerce')
    
    # 準備比對結果
    comparison_results = []
    
    # 逐時間點、逐履約價比對
    for _, calc_row in calculated_df.iterrows():
        # 將時間轉換為 6 位字串格式（與 PROD 一致，如 084515）
        time_raw = calc_row['Time']
        time_val = str(int(time_raw)).zfill(6) if pd.notna(time_raw) else ''
        strike_val = int(float(calc_row['Strike']))
        
        # 找到對應的 PROD 資料行
        prod_match = prod_df[
            (prod_df['time'] == time_val) & 
            (pd.to_numeric(prod_df['strike'], errors='coerce') == strike_val)
        ]
        
        if prod_match.empty:
            continue
        
        prod_row = prod_match.iloc[0]
        
        # 取得計算結果
        calc_bid = calc_row['Q_hat_Bid']
        calc_ask = calc_row['Q_hat_Ask']
        
        # 取得官方結果
        prod_bid = prod_row[prod_bid_col]
        prod_ask = prod_row[prod_ask_col]
        
        # 比對
        bid_match = False
        ask_match = False
        
        if pd.notna(calc_bid) and pd.notna(prod_bid):
            bid_match = abs(float(calc_bid) - float(prod_bid)) < 0.01
        elif pd.isna(calc_bid) and pd.isna(prod_bid):
            bid_match = True
        
        if pd.notna(calc_ask) and pd.notna(prod_ask):
            ask_match = abs(float(calc_ask) - float(prod_ask)) < 0.01
        elif pd.isna(calc_ask) and pd.isna(prod_ask):
            ask_match = True
        
        comparison_results.append({
            'Time': time_val,
            'Strike': strike_val,
            'CP': cp,
            'Calc_Bid': calc_bid,
            'Calc_Ask': calc_ask,
            'PROD_Bid': prod_bid,
            'PROD_Ask': prod_ask,
            'Bid_Match': bid_match,
            'Ask_Match': ask_match,
            'Q_hat_Source': calc_row.get('Q_hat_Source', ''),
            'EMA': calc_row.get('EMA', ''),
            'Gamma': calc_row.get(f'Q_{cp == "C" and "Last" or "Last"}_Valid_Gamma', ''),
            'Is_Outlier': calc_row.get(f'Q_{"Last"}_Valid_Is_Outlier', ''),
            'Outlier_Reason': calc_row.get(f'Q_{"Last"}_Valid_Outlier_Reason', ''),
        })
    
    return pd.DataFrame(comparison_results)


def main():
    """主程式"""
    print("=" * 80)
    print("Step 0 驗證：前 10 個時間區間篩選結果比對")
    print("=" * 80)
    print()
    
    # === 載入官方 PROD 資料 ===
    near_prod_path = r"c:\AGY\VIX\VIX\資料來源\20251231\NearPROD_20251231.tsv"
    next_prod_path = r"c:\AGY\VIX\VIX\資料來源\20251231\NextPROD_20251231.tsv"
    
    print(">>> 載入官方 PROD 資料...")
    near_prod, near_times = load_prod_data(near_prod_path, num_times=10)
    next_prod, next_times = load_prod_data(next_prod_path, num_times=10)
    
    print(f"  Near Term: {len(near_prod)} 筆, {len(near_times)} 個時間區間")
    print(f"  Next Term: {len(next_prod)} 筆, {len(next_times)} 個時間區間")
    print()
    
    # === 載入步驟一結果 (如果之前已經產生過) ===
    # 這裡我們需要先確認步驟一的輸入資料
    # 由於步驟一需要原始報價資料，這裡我們先嘗試讀取之前產生的 CSV
    
    step1_near_csv = "step0_1_valid_quotes_Near_測試前10個.csv"
    step1_next_csv = "step0_1_valid_quotes_Next_測試前10個.csv"
    
    if not os.path.exists(step1_near_csv):
        print("!!! 步驟一結果檔案不存在，請先執行 step0_valid_quotes.py")
        print("  缺少: " + step1_near_csv)
        return
    
    # === 載入步驟一結果並執行步驟二、三 ===
    print(">>> 載入步驟一結果...")
    near_df = pd.read_csv(step1_near_csv)
    next_df = pd.read_csv(step1_next_csv)
    
    print(f"  Near Term: {len(near_df)} 筆")
    print(f"  Next Term: {len(next_df)} 筆")
    print()
    
    # === 執行步驟二、三 ===
    print(">>> 執行步驟二、三（EMA 計算、異常值判定、篩選後報價決定）...")
    print()
    
    print("【Near Term】")
    near_with_ema = add_ema_and_outlier_detection(near_df, 'Near')
    
    print()
    print("【Next Term】")
    next_with_ema = add_ema_and_outlier_detection(next_df, 'Next')
    print()
    
    # === 輸出詳細計算過程 ===
    print("=" * 80)
    print("Step 0 計算過程詳細輸出（示範：Near Term 前 3 個序列 × 前 3 個時間點）")
    print("=" * 80)
    print()
    
    # 選擇前 3 個 Strike + CP 組合來展示
    sample_series = near_with_ema.groupby(['Strike', 'CP']).head(3)
    unique_series = near_with_ema[['Strike', 'CP']].drop_duplicates().head(3)
    
    for _, series_info in unique_series.iterrows():
        strike = series_info['Strike']
        cp = series_info['CP']
        
        print(f"【序列: Strike={strike}, CP={cp}】")
        print("-" * 60)
        
        series_data = near_with_ema[
            (near_with_ema['Strike'] == strike) & 
            (near_with_ema['CP'] == cp)
        ].head(3)
        
        for _, row in series_data.iterrows():
            print(f"  時間: {row['Time']}")
            print(f"    Q_Last_Valid: Bid={row.get('Q_Last_Valid_Bid', 'N/A')}, Ask={row.get('Q_Last_Valid_Ask', 'N/A')}, Mid={row.get('Q_Last_Valid_Mid', 'N/A')}")
            print(f"    Q_Min_Valid:  Bid={row.get('Q_Min_Valid_Bid', 'N/A')}, Ask={row.get('Q_Min_Valid_Ask', 'N/A')}, Mid={row.get('Q_Min_Valid_Mid', 'N/A')}")
            print(f"    EMA: {row.get('EMA', 'N/A')}")
            print(f"    Q_Last_Valid Gamma: {row.get('Q_Last_Valid_Gamma', 'N/A')}")
            print(f"    Q_Min_Valid Gamma:  {row.get('Q_Min_Valid_Gamma', 'N/A')}")
            print(f"    Q_Last_Valid 異常值: {row.get('Q_Last_Valid_Is_Outlier', 'N/A')} - {row.get('Q_Last_Valid_Outlier_Reason', 'N/A')}")
            print(f"    Q_Min_Valid 異常值:  {row.get('Q_Min_Valid_Is_Outlier', 'N/A')} - {row.get('Q_Min_Valid_Outlier_Reason', 'N/A')}")
            print(f"    條件判定 (Q_Last): Cond1={row.get('Q_Last_Valid_Cond_1', 'N/A')}, Cond2={row.get('Q_Last_Valid_Cond_2', 'N/A')}, Cond3={row.get('Q_Last_Valid_Cond_3', 'N/A')}, Cond4={row.get('Q_Last_Valid_Cond_4', 'N/A')}")
            print(f"    >>> 最終報價 Q_hat: Bid={row.get('Q_hat_Bid', 'N/A')}, Ask={row.get('Q_hat_Ask', 'N/A')}, 來源={row.get('Q_hat_Source', 'N/A')}")
            print()
        print()
    
    # === 儲存完整結果 ===
    output_near = "step0_full_output_Near_前10個.csv"
    output_next = "step0_full_output_Next_前10個.csv"
    
    near_with_ema.to_csv(output_near, index=False, encoding='utf-8-sig')
    next_with_ema.to_csv(output_next, index=False, encoding='utf-8-sig')
    
    print(f">>> 完整結果已儲存:")
    print(f"    {output_near}")
    print(f"    {output_next}")
    print()
    
    # === 與 PROD 資料比對 ===
    print("=" * 80)
    print("與官方 PROD 資料比對")
    print("=" * 80)
    print()
    
    # 由於步驟一的資料可能與 PROD 的時間範圍不同，這裡只比對重疊的部分
    # PROD 從 084515 開始，我們從計算結果過濾掉 084500
    
    # Near Term - Call
    print("【Near Term - Call 比對】")
    near_call = near_with_ema[(near_with_ema['CP'] == 'Call') & (near_with_ema['Time'] != 84500)].copy()
    near_call_compare = compare_results(near_call, near_prod, 'Near', 'C')
    
    if not near_call_compare.empty:
        total = len(near_call_compare)
        bid_match_count = near_call_compare['Bid_Match'].sum()
        ask_match_count = near_call_compare['Ask_Match'].sum()
        print(f"  Bid 匹配: {bid_match_count}/{total} ({100*bid_match_count/total:.1f}%)")
        print(f"  Ask 匹配: {ask_match_count}/{total} ({100*ask_match_count/total:.1f}%)")
        
        # 顯示不匹配的項目
        mismatches = near_call_compare[~(near_call_compare['Bid_Match'] & near_call_compare['Ask_Match'])]
        if not mismatches.empty:
            print(f"  不匹配項目（前 5 筆）:")
            print(mismatches[['Time', 'Strike', 'Calc_Bid', 'PROD_Bid', 'Calc_Ask', 'PROD_Ask', 'Q_hat_Source']].head().to_string(index=False))
    else:
        print("  （無重疊資料可比對）")
    print()
    
    # Near Term - Put
    print("【Near Term - Put 比對】")
    near_put = near_with_ema[(near_with_ema['CP'] == 'Put') & (near_with_ema['Time'] != 84500)].copy()
    near_put_compare = compare_results(near_put, near_prod, 'Near', 'P')
    
    if not near_put_compare.empty:
        total = len(near_put_compare)
        bid_match_count = near_put_compare['Bid_Match'].sum()
        ask_match_count = near_put_compare['Ask_Match'].sum()
        print(f"  Bid 匹配: {bid_match_count}/{total} ({100*bid_match_count/total:.1f}%)")
        print(f"  Ask 匹配: {ask_match_count}/{total} ({100*ask_match_count/total:.1f}%)")
    else:
        print("  （無重疊資料可比對）")
    print()
    
    # 儲存比對結果
    comparison_output = "step0_comparison_with_PROD.csv"
    all_compare = pd.concat([near_call_compare, near_put_compare], ignore_index=True)
    if not all_compare.empty:
        all_compare.to_csv(comparison_output, index=False, encoding='utf-8-sig')
        print(f">>> 比對結果已儲存: {comparison_output}")
    
    print()
    print("=" * 80)
    print("測試完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
