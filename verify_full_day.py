"""
VIX Step 0 全天驗證腳本
比對我們的計算結果與 PROD 資料
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
    print("VIX Step 0 全天驗證")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # ========== 載入資料 ==========
    print("\n>>> 載入資料...")
    
    # PROD 資料
    near_prod = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
    next_prod = pd.read_csv(r'資料來源\20251231\NextPROD_20251231.tsv', sep='\t', dtype=str)
    
    # 我們的計算結果
    near_calc = pd.read_csv('step0_full_output_Near_全天.csv')
    next_calc = pd.read_csv('step0_full_output_Next_全天.csv')
    
    print(f"    PROD Near: {len(near_prod)} 筆")
    print(f"    PROD Next: {len(next_prod)} 筆")
    print(f"    我們 Near: {len(near_calc)} 筆")
    print(f"    我們 Next: {len(next_calc)} 筆")
    
    # ========== 驗證 Near Term ==========
    print("\n" + "=" * 80)
    print("驗證 Near Term")
    print("=" * 80)
    
    near_results = verify_term(near_prod, near_calc, 'Near')
    
    # ========== 驗證 Next Term ==========
    print("\n" + "=" * 80)
    print("驗證 Next Term")
    print("=" * 80)
    
    next_results = verify_term(next_prod, next_calc, 'Next')
    
    # ========== 總結 ==========
    print("\n" + "=" * 80)
    print("驗證總結")
    print("=" * 80)
    
    print("\n【Near Term】")
    print_summary(near_results)
    
    print("\n【Next Term】")
    print_summary(next_results)
    
    # 儲存詳細結果
    save_detailed_results(near_results, 'Near')
    save_detailed_results(next_results, 'Next')

def verify_term(prod_df, calc_df, term_name):
    """驗證單一 Term 的所有資料"""
    
    results = {
        'total_compared': 0,
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
    
    # 過濾有效的 PROD 資料（有 strike 的）
    prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
    
    print(f"  有效 PROD 筆數: {len(prod_valid)}")
    
    # 逐筆比對
    for _, prod_row in prod_valid.iterrows():
        time_str = prod_row['time']
        time_int = int(time_str)
        strike = int(prod_row['strike'])
        
        # 比對 Call
        compare_single(prod_row, calc_df, time_int, strike, 'Call', 'c', results)
        
        # 比對 Put
        compare_single(prod_row, calc_df, time_int, strike, 'Put', 'p', results)
    
    return results

def compare_single(prod_row, calc_df, time_int, strike, cp, prefix, results):
    """比對單一 (Time, Strike, CP) 的資料"""
    
    # 找對應的計算結果
    calc_row = calc_df[(calc_df['Time'] == time_int) & 
                       (calc_df['Strike'] == strike) & 
                       (calc_df['CP'] == cp)]
    
    if calc_row.empty:
        return
    
    calc_row = calc_row.iloc[0]
    results['total_compared'] += 1
    
    # ----- EMA 比對 -----
    prod_ema = prod_row[f'{prefix}.ema']
    our_ema = calc_row['EMA']
    
    try:
        if pd.notna(prod_ema) and prod_ema != '' and pd.notna(our_ema):
            if abs(float(prod_ema) - float(our_ema)) < 1e-4:
                results['ema_match'] += 1
            else:
                results['ema_mismatch'].append({
                    'Time': time_int, 'Strike': strike, 'CP': cp,
                    'PROD': float(prod_ema), 'OURS': float(our_ema),
                    'Diff': abs(float(prod_ema) - float(our_ema))
                })
        elif pd.isna(prod_ema) or prod_ema == '':
            results['ema_match'] += 1  # PROD 無資料視為通過
    except:
        pass
    
    # ----- Q_hat (最終報價) 比對 -----
    prod_bid = prod_row[f'{prefix}.bid']
    prod_ask = prod_row[f'{prefix}.ask']
    our_bid = calc_row['Q_hat_Bid']
    our_ask = calc_row['Q_hat_Ask']
    
    try:
        bid_match = int(float(prod_bid)) == int(float(our_bid)) if pd.notna(prod_bid) and pd.notna(our_bid) else True
        ask_match = int(float(prod_ask)) == int(float(our_ask)) if pd.notna(prod_ask) and pd.notna(our_ask) else True
        
        if bid_match:
            results['q_hat_bid_match'] += 1
        if ask_match:
            results['q_hat_ask_match'] += 1
            
        if not bid_match or not ask_match:
            results['q_hat_mismatch'].append({
                'Time': time_int, 'Strike': strike, 'CP': cp,
                'PROD_Bid': prod_bid, 'PROD_Ask': prod_ask,
                'OURS_Bid': our_bid, 'OURS_Ask': our_ask
            })
    except:
        pass
    
    # ----- Q_Last 比對 -----
    prod_last_bid = prod_row[f'{prefix}.last_bid']
    prod_last_ask = prod_row[f'{prefix}.last_ask']
    our_last_bid = calc_row['Q_Last_Valid_Bid']
    our_last_ask = calc_row['Q_Last_Valid_Ask']
    
    try:
        last_bid_match = int(float(prod_last_bid)) == int(float(our_last_bid)) if pd.notna(prod_last_bid) and pd.notna(our_last_bid) else True
        last_ask_match = int(float(prod_last_ask)) == int(float(our_last_ask)) if pd.notna(prod_last_ask) and pd.notna(our_last_ask) else True
        
        if last_bid_match:
            results['q_last_bid_match'] += 1
        if last_ask_match:
            results['q_last_ask_match'] += 1
            
        if not last_bid_match or not last_ask_match:
            results['q_last_mismatch'].append({
                'Time': time_int, 'Strike': strike, 'CP': cp,
                'PROD_Bid': prod_last_bid, 'PROD_Ask': prod_last_ask,
                'OURS_Bid': our_last_bid, 'OURS_Ask': our_last_ask
            })
    except:
        pass
    
    # ----- Outlier 比對 -----
    prod_outlier = prod_row[f'{prefix}.last_outlier']
    our_outlier = calc_row['Q_Last_Valid_Is_Outlier']
    
    prod_is_outlier = convert_outlier(prod_outlier)
    
    if prod_is_outlier is not None:
        if prod_is_outlier == our_outlier:
            results['outlier_match'] += 1
        else:
            results['outlier_mismatch'].append({
                'Time': time_int, 'Strike': strike, 'CP': cp,
                'PROD': prod_outlier, 'OURS': our_outlier
            })
    
    # ----- Gamma 比對 -----
    prod_gamma = prod_row[f'{prefix}.gamma']
    our_gamma = calc_row['Q_Last_Valid_Gamma']
    
    try:
        if pd.notna(prod_gamma) and prod_gamma != '' and pd.notna(our_gamma):
            if abs(float(prod_gamma) - float(our_gamma)) < 0.01:
                results['gamma_match'] += 1
            else:
                results['gamma_mismatch'].append({
                    'Time': time_int, 'Strike': strike, 'CP': cp,
                    'PROD': float(prod_gamma), 'OURS': float(our_gamma)
                })
    except:
        pass

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
    
    # Gamma (已知有差異)
    if results['gamma_match'] + len(results['gamma_mismatch']) > 0:
        gamma_total = results['gamma_match'] + len(results['gamma_mismatch'])
        gamma_rate = results['gamma_match'] / gamma_total * 100
        print(f"  【Gamma】正確率: {results['gamma_match']}/{gamma_total} = {gamma_rate:.2f}% (已知有差異)")

def save_detailed_results(results, term_name):
    """儲存詳細的不一致案例"""
    
    if results['ema_mismatch']:
        df = pd.DataFrame(results['ema_mismatch'])
        filename = f'驗證結果_{term_name}_EMA不一致.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"  EMA 不一致詳情已儲存: {filename}")
    
    if results['q_hat_mismatch']:
        df = pd.DataFrame(results['q_hat_mismatch'])
        filename = f'驗證結果_{term_name}_Q_hat不一致.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"  Q_hat 不一致詳情已儲存: {filename}")
    
    if results['outlier_mismatch']:
        df = pd.DataFrame(results['outlier_mismatch'])
        filename = f'驗證結果_{term_name}_Outlier不一致.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"  Outlier 不一致詳情已儲存: {filename}")

if __name__ == "__main__":
    main()
