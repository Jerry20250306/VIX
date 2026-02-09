"""
VIX 差異分析腳本（優化版）
依照時間順序找出第一筆差異並詳細分析
使用 merge + 向量化比較，大幅提升效能
"""
import pandas as pd
import numpy as np

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

def main():
    print("=" * 80)
    print("VIX Step 0 差異分析 - 找出第一筆差異")
    print("=" * 80)
    
    # 載入資料
    print("\n>>> 載入資料...")
    
    # PROD 資料
    near_prod = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
    
    # 我們的計算結果
    near_calc = pd.read_csv('output/step0_full_output_Near_測試前30個.csv')
    
    print(f"    PROD: {len(near_prod)} 筆")
    print(f"    我們: {len(near_calc)} 筆")
    
    # 準備 PROD 資料
    prod_valid = near_prod[near_prod['strike'].notna() & (near_prod['strike'] != '')].copy()
    prod_valid['time_int'] = prod_valid['time'].astype(int)
    prod_valid['strike_int'] = prod_valid['strike'].astype(int)
    
    # =========================================================================
    # 優化：將 PROD 展開為 Call/Put 獨立的行，然後用 merge 一次比較
    # =========================================================================
    
    # 展開 Call
    prod_call = prod_valid[['time_int', 'strike_int', 
                            'c.bid', 'c.ask', 'c.last_bid', 'c.last_ask', 'c.last_outlier',
                            'c.min_bid', 'c.min_ask', 'c.min_outlier', 'c.ema', 'c.gamma']].copy()
    prod_call['CP'] = 'Call'
    prod_call = prod_call.rename(columns={
        'strike_int': 'Strike',
        'time_int': 'Time',
        'c.bid': 'PROD_Q_hat_Bid',
        'c.ask': 'PROD_Q_hat_Ask',
        'c.last_bid': 'PROD_Last_Bid',
        'c.last_ask': 'PROD_Last_Ask',
        'c.last_outlier': 'PROD_Last_Outlier',
        'c.min_bid': 'PROD_Min_Bid',
        'c.min_ask': 'PROD_Min_Ask',
        'c.min_outlier': 'PROD_Min_Outlier',
        'c.ema': 'PROD_EMA',
        'c.gamma': 'PROD_Gamma'
    })
    
    # 展開 Put
    prod_put = prod_valid[['time_int', 'strike_int',
                           'p.bid', 'p.ask', 'p.last_bid', 'p.last_ask', 'p.last_outlier',
                           'p.min_bid', 'p.min_ask', 'p.min_outlier', 'p.ema', 'p.gamma']].copy()
    prod_put['CP'] = 'Put'
    prod_put = prod_put.rename(columns={
        'strike_int': 'Strike',
        'time_int': 'Time',
        'p.bid': 'PROD_Q_hat_Bid',
        'p.ask': 'PROD_Q_hat_Ask',
        'p.last_bid': 'PROD_Last_Bid',
        'p.last_ask': 'PROD_Last_Ask',
        'p.last_outlier': 'PROD_Last_Outlier',
        'p.min_bid': 'PROD_Min_Bid',
        'p.min_ask': 'PROD_Min_Ask',
        'p.min_outlier': 'PROD_Min_Outlier',
        'p.ema': 'PROD_EMA',
        'p.gamma': 'PROD_Gamma'
    })
    
    # 合併 Call 和 Put
    prod_expanded = pd.concat([prod_call, prod_put], ignore_index=True)
    
    # 轉換 PROD 數值欄位
    for col in ['PROD_Q_hat_Bid', 'PROD_Q_hat_Ask', 'PROD_EMA', 'PROD_Gamma']:
        prod_expanded[col] = pd.to_numeric(prod_expanded[col], errors='coerce')
    
    # Merge：一次性合併 PROD 和我們的計算結果
    merged = pd.merge(
        near_calc,
        prod_expanded,
        on=['Time', 'Strike', 'CP'],
        how='inner'
    )
    
    print(f"    合併後: {len(merged)} 筆可比較")
    
    # =========================================================================
    # 向量化比較：一次找出所有差異
    # =========================================================================
    
    # Q_hat_Bid 差異
    merged['diff_Q_hat_Bid'] = (merged['Q_hat_Bid'].fillna(-1).astype(int) != 
                                merged['PROD_Q_hat_Bid'].fillna(-1).astype(int))
    
    # Q_hat_Ask 差異
    merged['diff_Q_hat_Ask'] = (merged['Q_hat_Ask'].fillna(-1).astype(int) != 
                                merged['PROD_Q_hat_Ask'].fillna(-1).astype(int))
    
    # EMA 差異 (容許 1e-4 誤差)
    merged['diff_EMA'] = (merged['EMA'].fillna(0) - merged['PROD_EMA'].fillna(0)).abs() >= 1e-4
    
    # Gamma 差異
    merged['diff_Gamma'] = (merged['Q_Last_Valid_Gamma'].fillna(0) - 
                            merged['PROD_Gamma'].fillna(0)).abs() >= 0.01
    
    # Outlier 差異：PROD 'V' = True outlier, 數字1-4 = False (符合某條件)
    def check_outlier_match(row):
        prod_val = row['PROD_Last_Outlier']
        our_val = row['Q_Last_Valid_Is_Outlier']
        if prod_val == 'V' and our_val != True:
            return True  # 差異
        elif prod_val not in ['V', '-', '', None] and not pd.isna(prod_val) and our_val != False:
            return True  # 差異
        return False
    
    merged['diff_Outlier'] = merged.apply(check_outlier_match, axis=1)
    
    # 任一差異
    merged['has_diff'] = (merged['diff_Q_hat_Bid'] | merged['diff_Q_hat_Ask'] | 
                          merged['diff_EMA'] | merged['diff_Gamma'] | merged['diff_Outlier'])
    
    # =========================================================================
    # 依時間順序找第一筆差異
    # =========================================================================
    
    print("\n" + "=" * 80)
    print("依時間順序分析差異")
    print("=" * 80)
    
    our_times = sorted(merged['Time'].unique())
    
    for time_int in our_times:
        print(f"\n>>> 分析時間點: {time_int}")
        
        time_data = merged[merged['Time'] == time_int]
        prod_strikes = len(time_data['Strike'].unique())
        
        print(f"    PROD 有 {prod_strikes} 個 Strike")
        print(f"    我們有 {len(time_data)} 筆（含 Call/Put）")
        
        # 找該時間點的差異
        diff_rows = time_data[time_data['has_diff']]
        
        if len(diff_rows) == 0:
            print(f"    [OK] 此時間點無差異")
            continue
        
        # 取第一筆差異
        first_diff = diff_rows.iloc[0]
        strike = first_diff['Strike']
        cp = first_diff['CP']
        prefix = 'c' if cp == 'Call' else 'p'
        
        print(f"\n    [差異] Strike={strike}, CP={cp}")
        print(f"    " + "-" * 60)
        
        # 列出具體差異
        if first_diff['diff_Q_hat_Bid']:
            print(f"    Q_hat_Bid:")
            print(f"        PROD: {first_diff['PROD_Q_hat_Bid']}")
            print(f"        我們: {first_diff['Q_hat_Bid']}")
        
        if first_diff['diff_Q_hat_Ask']:
            print(f"    Q_hat_Ask:")
            print(f"        PROD: {first_diff['PROD_Q_hat_Ask']}")
            print(f"        我們: {first_diff['Q_hat_Ask']}")
        
        if first_diff['diff_EMA']:
            print(f"    EMA:")
            print(f"        PROD: {first_diff['PROD_EMA']}")
            print(f"        我們: {first_diff['EMA']}")
        
        if first_diff['diff_Gamma']:
            print(f"    Gamma:")
            print(f"        PROD: {first_diff['PROD_Gamma']}")
            print(f"        我們: {first_diff['Q_Last_Valid_Gamma']}")
        
        if first_diff['diff_Outlier']:
            print(f"    Outlier:")
            print(f"        PROD: {first_diff['PROD_Last_Outlier']}")
            print(f"        我們: {first_diff['Q_Last_Valid_Is_Outlier']}")
        
        # 列印完整比較資訊
        print(f"\n    【完整 PROD 資料】")
        print(f"        {prefix}.bid = {first_diff['PROD_Q_hat_Bid']}")
        print(f"        {prefix}.ask = {first_diff['PROD_Q_hat_Ask']}")
        print(f"        {prefix}.last_bid = {first_diff['PROD_Last_Bid']}")
        print(f"        {prefix}.last_ask = {first_diff['PROD_Last_Ask']}")
        print(f"        {prefix}.last_outlier = {first_diff['PROD_Last_Outlier']}")
        print(f"        {prefix}.min_bid = {first_diff['PROD_Min_Bid']}")
        print(f"        {prefix}.min_ask = {first_diff['PROD_Min_Ask']}")
        print(f"        {prefix}.min_outlier = {first_diff['PROD_Min_Outlier']}")
        print(f"        {prefix}.ema = {first_diff['PROD_EMA']}")
        print(f"        {prefix}.gamma = {first_diff['PROD_Gamma']}")
        
        print(f"\n    【我們的計算結果】")
        print(f"        Q_hat_Bid = {first_diff['Q_hat_Bid']}")
        print(f"        Q_hat_Ask = {first_diff['Q_hat_Ask']}")
        print(f"        Q_hat_Source = {first_diff['Q_hat_Source']}")
        print(f"        Q_Last_Valid_Bid = {first_diff['Q_Last_Valid_Bid']}")
        print(f"        Q_Last_Valid_Ask = {first_diff['Q_Last_Valid_Ask']}")
        print(f"        Q_Last_Valid_Is_Outlier = {first_diff['Q_Last_Valid_Is_Outlier']}")
        print(f"        Q_Min_Valid_Bid = {first_diff['Q_Min_Valid_Bid']}")
        print(f"        Q_Min_Valid_Ask = {first_diff['Q_Min_Valid_Ask']}")
        print(f"        Q_Min_Valid_Is_Outlier = {first_diff['Q_Min_Valid_Is_Outlier']}")
        print(f"        EMA = {first_diff['EMA']}")
        print(f"        Q_Last_Valid_Gamma = {first_diff['Q_Last_Valid_Gamma']}")
        
        print("\n" + "=" * 80)
        print("分析結束：已找到第一筆差異")
        print("=" * 80)
        return  # 找到第一筆差異就停止
    
    print("\n" + "=" * 80)
    print("[OK] 全部時間點驗證通過，無任何差異！")
    print("=" * 80)

if __name__ == "__main__":
    main()
