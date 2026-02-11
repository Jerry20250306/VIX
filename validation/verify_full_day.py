"""
VIX Step 0 驗證腳本（優化版）
使用 pandas merge 取代逐筆比對，大幅提升效能
"""
import pandas as pd
import numpy as np
from datetime import datetime

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

def convert_outlier(prod_value):
    """將 PROD 異常值標記轉換為布林值"""
    if prod_value == 'V':
        return True
    elif prod_value == '-' or prod_value == '' or pd.isna(prod_value):
        return None
    else:
        return False

def main():
    print("=" * 80)
    print("VIX Step 0 驗證（優化版）")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # ========== 載入資料 ==========
    print("\n>>> 載入資料...")
    
    # PROD 資料
    near_prod = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
    next_prod = pd.read_csv(r'資料來源\20251231\NextPROD_20251231.tsv', sep='\t', dtype=str)
    
    # 我們的計算結果
    near_calc = pd.read_csv('step0_full_output_Near_測試前30個.csv')
    next_calc = pd.read_csv('step0_full_output_Next_測試前30個.csv')
    
    print(f"    PROD Near: {len(near_prod)} 筆")
    print(f"    PROD Next: {len(next_prod)} 筆")
    print(f"    我們 Near: {len(near_calc)} 筆")
    print(f"    我們 Next: {len(next_calc)} 筆")
    
    # ========== 驗證 Near Term ==========
    print("\n" + "=" * 80)
    print("驗證 Near Term")
    print("=" * 80)
    
    near_results = verify_term_fast(near_prod, near_calc, 'Near')
    
    # ========== 驗證 Next Term ==========
    print("\n" + "=" * 80)
    print("驗證 Next Term")
    print("=" * 80)
    
    next_results = verify_term_fast(next_prod, next_calc, 'Next')
    
    # ========== 總結 ==========
    print("\n" + "=" * 80)
    print("驗證總結")
    print("=" * 80)
    
    print("\n【Near Term】")
    print_summary(near_results)
    
    print("\n【Next Term】")
    print_summary(next_results)

def verify_term_fast(prod_df, calc_df, term_name):
    """使用 pandas merge 快速驗證（比逐筆比對快 100 倍以上）"""
    
    print(f"  使用 pandas merge 進行快速比對...")
    
    # 1. 準備 PROD 資料（展開為 Call/Put 兩列）
    prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
    prod_valid['time_int'] = prod_valid['time'].astype(int)
    prod_valid['strike_int'] = prod_valid['strike'].astype(int)
    
    # 建立 Call 和 Put 的獨立 DataFrame
    prod_call = prod_valid[['time_int', 'strike_int', 'c.ema', 'c.gamma', 
                            'c.last_bid', 'c.last_ask', 'c.last_outlier',
                            'c.min_bid', 'c.min_ask', 'c.min_outlier',
                            'c.bid', 'c.ask']].copy()
    prod_call['CP'] = 'Call'
    prod_call.columns = ['Time', 'Strike', 'PROD_EMA', 'PROD_Gamma',
                         'PROD_Last_Bid', 'PROD_Last_Ask', 'PROD_Last_Outlier',
                         'PROD_Min_Bid', 'PROD_Min_Ask', 'PROD_Min_Outlier',
                         'PROD_Q_hat_Bid', 'PROD_Q_hat_Ask', 'CP']
    
    prod_put = prod_valid[['time_int', 'strike_int', 'p.ema', 'p.gamma',
                           'p.last_bid', 'p.last_ask', 'p.last_outlier',
                           'p.min_bid', 'p.min_ask', 'p.min_outlier',
                           'p.bid', 'p.ask']].copy()
    prod_put['CP'] = 'Put'
    prod_put.columns = ['Time', 'Strike', 'PROD_EMA', 'PROD_Gamma',
                        'PROD_Last_Bid', 'PROD_Last_Ask', 'PROD_Last_Outlier',
                        'PROD_Min_Bid', 'PROD_Min_Ask', 'PROD_Min_Outlier',
                        'PROD_Q_hat_Bid', 'PROD_Q_hat_Ask', 'CP']
    
    prod_long = pd.concat([prod_call, prod_put], ignore_index=True)
    
    # 2. 準備我們的計算結果
    calc_subset = calc_df[['Time', 'Strike', 'CP', 'EMA', 
                           'Q_Last_Valid_Bid', 'Q_Last_Valid_Ask', 'Q_Last_Valid_Is_Outlier', 'Q_Last_Valid_Gamma',
                           'Q_Min_Valid_Bid', 'Q_Min_Valid_Ask', 'Q_Min_Valid_Is_Outlier',
                           'Q_hat_Bid', 'Q_hat_Ask', 'Q_hat_Source']].copy()
    
    # 3. 使用 merge 進行比對（關鍵優化！）
    merged = pd.merge(prod_long, calc_subset, on=['Time', 'Strike', 'CP'], how='inner')
    
    print(f"  成功配對: {len(merged)} 筆")
    
    # 4. 計算各項指標
    results = {
        'total_compared': len(merged),
        'ema_match': 0,
        'ema_mismatch': [],
        'q_hat_bid_match': 0,
        'q_hat_ask_match': 0,
        'q_hat_mismatch': [],
        'q_last_bid_match': 0,
        'q_last_ask_match': 0,
        'q_last_mismatch': [],
        'outlier_match': 0,
        'outlier_mismatch': [],
        'gamma_match': 0,
        'gamma_mismatch': [],
    }
    
    if len(merged) == 0:
        return results
    
    # ----- EMA 比對（向量化）-----
    merged['PROD_EMA_float'] = pd.to_numeric(merged['PROD_EMA'], errors='coerce')
    merged['EMA_float'] = pd.to_numeric(merged['EMA'], errors='coerce')
    merged['EMA_diff'] = (merged['PROD_EMA_float'] - merged['EMA_float']).abs()
    
    ema_valid = merged['PROD_EMA_float'].notna() & merged['EMA_float'].notna()
    ema_match = (merged['EMA_diff'] < 1e-4) | ~ema_valid
    results['ema_match'] = ema_match.sum()
    
    ema_mismatch_df = merged[ema_valid & (merged['EMA_diff'] >= 1e-4)][['Time', 'Strike', 'CP', 'PROD_EMA_float', 'EMA_float', 'EMA_diff']]
    results['ema_mismatch'] = ema_mismatch_df.to_dict('records')
    
    # ----- Q_hat 比對（向量化）-----
    merged['PROD_Bid_float'] = pd.to_numeric(merged['PROD_Q_hat_Bid'], errors='coerce')
    merged['PROD_Ask_float'] = pd.to_numeric(merged['PROD_Q_hat_Ask'], errors='coerce')
    merged['OURS_Bid_float'] = pd.to_numeric(merged['Q_hat_Bid'], errors='coerce')
    merged['OURS_Ask_float'] = pd.to_numeric(merged['Q_hat_Ask'], errors='coerce')
    
    # 比較整數部分（忽略 NaN）
    bid_match = (merged['PROD_Bid_float'].fillna(-999).astype(int) == merged['OURS_Bid_float'].fillna(-999).astype(int)) | merged['PROD_Bid_float'].isna()
    ask_match = (merged['PROD_Ask_float'].fillna(-999).astype(int) == merged['OURS_Ask_float'].fillna(-999).astype(int)) | merged['PROD_Ask_float'].isna()
    
    results['q_hat_bid_match'] = bid_match.sum()
    results['q_hat_ask_match'] = ask_match.sum()
    
    q_hat_mismatch_df = merged[~bid_match | ~ask_match][['Time', 'Strike', 'CP', 'PROD_Q_hat_Bid', 'PROD_Q_hat_Ask', 'Q_hat_Bid', 'Q_hat_Ask', 'Q_hat_Source']]
    results['q_hat_mismatch'] = q_hat_mismatch_df.head(100).to_dict('records')  # 限制筆數避免過多
    
    # ----- Q_Last 比對（向量化）-----
    merged['PROD_Last_Bid_float'] = pd.to_numeric(merged['PROD_Last_Bid'], errors='coerce')
    merged['PROD_Last_Ask_float'] = pd.to_numeric(merged['PROD_Last_Ask'], errors='coerce')
    merged['OURS_Last_Bid_float'] = pd.to_numeric(merged['Q_Last_Valid_Bid'], errors='coerce')
    merged['OURS_Last_Ask_float'] = pd.to_numeric(merged['Q_Last_Valid_Ask'], errors='coerce')
    
    last_bid_match = (merged['PROD_Last_Bid_float'].fillna(-999).astype(int) == merged['OURS_Last_Bid_float'].fillna(-999).astype(int)) | merged['PROD_Last_Bid_float'].isna()
    last_ask_match = (merged['PROD_Last_Ask_float'].fillna(-999).astype(int) == merged['OURS_Last_Ask_float'].fillna(-999).astype(int)) | merged['PROD_Last_Ask_float'].isna()
    
    results['q_last_bid_match'] = last_bid_match.sum()
    results['q_last_ask_match'] = last_ask_match.sum()
    
    # ----- Outlier 比對（向量化）-----
    merged['PROD_Outlier_bool'] = merged['PROD_Last_Outlier'].apply(convert_outlier)
    outlier_valid = merged['PROD_Outlier_bool'].notna()
    outlier_match = merged['PROD_Outlier_bool'] == merged['Q_Last_Valid_Is_Outlier']
    
    results['outlier_match'] = (outlier_valid & outlier_match).sum()
    outlier_mismatch_df = merged[outlier_valid & ~outlier_match][['Time', 'Strike', 'CP', 'PROD_Last_Outlier', 'Q_Last_Valid_Is_Outlier']]
    results['outlier_mismatch'] = outlier_mismatch_df.head(100).to_dict('records')
    
    # ----- Gamma 比對（向量化）-----
    merged['PROD_Gamma_float'] = pd.to_numeric(merged['PROD_Gamma'], errors='coerce')
    merged['OURS_Gamma_float'] = pd.to_numeric(merged['Q_Last_Valid_Gamma'], errors='coerce')
    
    gamma_valid = merged['PROD_Gamma_float'].notna() & merged['OURS_Gamma_float'].notna()
    gamma_diff = (merged['PROD_Gamma_float'] - merged['OURS_Gamma_float']).abs()
    gamma_match = (gamma_diff < 0.01) | ~gamma_valid
    
    results['gamma_match'] = gamma_match.sum()
    gamma_mismatch_df = merged[gamma_valid & (gamma_diff >= 0.01)][['Time', 'Strike', 'CP', 'PROD_Gamma_float', 'OURS_Gamma_float']]
    results['gamma_mismatch'] = gamma_mismatch_df.head(100).to_dict('records')
    
    return results

def print_summary(results):
    """列印驗證摘要"""
    total = results['total_compared']
    
    if total == 0:
        print("  無資料可比對")
        return
    
    print(f"  總比對筆數: {total}")
    print()
    
    # EMA
    ema_rate = results['ema_match'] / total * 100
    print(f"  【EMA】正確率: {results['ema_match']}/{total} = {ema_rate:.2f}%")
    if results['ema_mismatch']:
        print(f"         不一致: {len(results['ema_mismatch'])} 筆")
    
    # Q_hat
    bid_rate = results['q_hat_bid_match'] / total * 100
    ask_rate = results['q_hat_ask_match'] / total * 100
    print(f"  【Q_hat Bid】正確率: {results['q_hat_bid_match']}/{total} = {bid_rate:.2f}%")
    print(f"  【Q_hat Ask】正確率: {results['q_hat_ask_match']}/{total} = {ask_rate:.2f}%")
    if results['q_hat_mismatch']:
        print(f"         不一致: {len(results['q_hat_mismatch'])} 筆")
    
    # Q_Last
    last_bid_rate = results['q_last_bid_match'] / total * 100
    last_ask_rate = results['q_last_ask_match'] / total * 100
    print(f"  【Q_Last Bid】正確率: {results['q_last_bid_match']}/{total} = {last_bid_rate:.2f}%")
    print(f"  【Q_Last Ask】正確率: {results['q_last_ask_match']}/{total} = {last_ask_rate:.2f}%")
    
    # Outlier
    if results['outlier_match'] + len(results['outlier_mismatch']) > 0:
        outlier_total = results['outlier_match'] + len(results['outlier_mismatch'])
        outlier_rate = results['outlier_match'] / outlier_total * 100
        print(f"  【Outlier】正確率: {results['outlier_match']}/{outlier_total} = {outlier_rate:.2f}%")
    
    # Gamma
    if results['gamma_match'] + len(results['gamma_mismatch']) > 0:
        gamma_total = results['gamma_match'] + len(results['gamma_mismatch'])
        gamma_rate = results['gamma_match'] / gamma_total * 100
        print(f"  【Gamma】正確率: {results['gamma_match']}/{gamma_total} = {gamma_rate:.2f}%")

if __name__ == "__main__":
    main()
